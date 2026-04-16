import json

from app.core.config import get_settings
from app.core.database import get_connection
from app.core.exceptions import AppError, NotFoundError
from app.core.ids import new_id
from app.core.time import utc_now_iso
from app.repositories.memory_summaries import MemorySummaryRepository
from app.repositories.messages import MessageRepository
from app.repositories.sessions import SessionRepository
from app.repositories.states import StateRepository
from app.schemas.memory_summaries import (
    MemorySummaryGenerateResponse,
    MemorySummaryResponse,
)
from app.schemas.models import ModelChatRequest
from app.services.model_router import ModelRouterService


def _row_to_response(row) -> MemorySummaryResponse:
    key_events: list[str] = []
    if row["key_events"]:
        try:
            parsed = json.loads(row["key_events"])
            if isinstance(parsed, list):
                key_events = [str(item).strip() for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            key_events = []

    return MemorySummaryResponse(
        id=row["id"],
        session_id=row["session_id"],
        segment_start=row["segment_start"],
        segment_end=row["segment_end"],
        summary=row["summary"],
        key_events=key_events,
        state_snapshot_id=row["state_snapshot_id"],
        frozen=bool(row["frozen"]),
        created_at=row["created_at"],
    )


class MemorySummaryService:
    def __init__(self) -> None:
        self.model_router = ModelRouterService()

    def _build_segment_rows(self, *, connection, session_id: str) -> list:
        messages = MessageRepository(connection)
        repository = MemorySummaryRepository(connection)
        settings = get_settings()

        visible_rows = messages.list_messages_by_session(session_id)
        if len(visible_rows) <= settings.memory_recent_raw_message_count:
            return []

        latest_summary = repository.get_latest_summary(session_id)
        last_segment_end = latest_summary["segment_end"] if latest_summary else 0

        candidate_rows = [
            row for row in visible_rows if int(row["sequence"]) > last_segment_end
        ]
        if len(candidate_rows) <= settings.memory_recent_raw_message_count:
            return []

        summarizable_rows = candidate_rows[: -settings.memory_recent_raw_message_count]
        if len(summarizable_rows) < settings.memory_summary_segment_size:
            return []

        return summarizable_rows[: settings.memory_summary_segment_size]

    def _fallback_summary(self, segment_rows: list, mode: str) -> tuple[str, list[str]]:
        lines: list[str] = []
        key_events: list[str] = []
        for row in segment_rows:
            role = "用户" if row["role"] == "user" else "助手"
            content = (row["content"] or "").strip().replace("\r", " ").replace("\n", " ")
            if not content:
                continue
            compact = content[:120]
            if len(content) > 120:
                compact += "..."
            line = f"{role}#{row['sequence']}: {compact}"
            lines.append(line)
            if len(key_events) < 5:
                key_events.append(compact)

        if not lines:
            summary = f"本段对话暂无可提炼内容。模式：{mode}。"
        else:
            summary = (
                f"本段对话共 {len(segment_rows)} 条消息，模式为 {mode}。\n"
                "按顺序概括如下：\n"
                + "\n".join(f"- {line}" for line in lines[:8])
            )
        return summary, key_events[:5]

    def _render_segment_text(self, segment_rows: list) -> str:
        rendered_lines: list[str] = []
        for row in segment_rows:
            role = row["role"]
            label = "User" if role == "user" else "Assistant"
            rendered_lines.append(
                f"[{row['sequence']}] {label}: {(row['content'] or '').strip()}"
            )
        return "\n".join(rendered_lines)

    def _parse_model_summary(self, content: str) -> tuple[str, list[str]]:
        cleaned = content.strip()
        if not cleaned:
            return "", []
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            return cleaned, []

        if not isinstance(parsed, dict):
            return cleaned, []

        summary = str(parsed.get("summary") or "").strip()
        raw_key_events = parsed.get("key_events")
        key_events: list[str] = []
        if isinstance(raw_key_events, list):
            key_events = [str(item).strip() for item in raw_key_events if str(item).strip()]
        return summary or cleaned, key_events[:5]

    def _generate_summary_content(
        self,
        *,
        session_row,
        segment_rows: list,
    ) -> tuple[str, list[str]]:
        settings = get_settings()
        segment_text = self._render_segment_text(segment_rows)
        target_model = session_row["model_name"] or settings.default_chat_model
        prompt_messages = [
            {
                "role": "system",
                "content": (
                    "You are generating a mid-term conversation memory for a roleplay/chat product. "
                    "Return valid JSON only with keys summary and key_events. "
                    "summary must be concise but preserve story progression, relationship changes, important decisions, "
                    "and state changes. key_events must be an array of 1 to 5 short strings."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Mode: {session_row['mode']}\n"
                    f"Conversation segment: {segment_rows[0]['sequence']} - {segment_rows[-1]['sequence']}\n\n"
                    "Messages:\n"
                    f"{segment_text}"
                ),
            },
        ]

        try:
            result = self.model_router.chat(
                ModelChatRequest(
                    model_name=target_model,
                    mode=session_row["mode"],
                    messages=prompt_messages,
                    temperature=0.2,
                    max_tokens=500,
                )
            )
            summary, key_events = self._parse_model_summary(result.content)
            if summary:
                return summary, key_events
        except AppError:
            pass

        return self._fallback_summary(segment_rows, session_row["mode"])

    def maybe_generate_next_summary(
        self,
        *,
        session_id: str,
        connection=None,
    ) -> MemorySummaryGenerateResponse:
        if connection is not None:
            return self._maybe_generate_next_summary_with_connection(
                session_id=session_id,
                connection=connection,
            )
        with get_connection() as new_connection:
            return self._maybe_generate_next_summary_with_connection(
                session_id=session_id,
                connection=new_connection,
            )

    def _maybe_generate_next_summary_with_connection(
        self,
        *,
        session_id: str,
        connection,
    ) -> MemorySummaryGenerateResponse:
        sessions = SessionRepository(connection)
        summaries = MemorySummaryRepository(connection)
        states = StateRepository(connection)

        session_row = sessions.get_session(session_id)
        if session_row is None:
            raise NotFoundError(f"Session not found: {session_id}")

        segment_rows = self._build_segment_rows(
            connection=connection,
            session_id=session_id,
        )
        if not segment_rows:
            return MemorySummaryGenerateResponse(created=False, summary=None)

        summary_text, key_events = self._generate_summary_content(
            session_row=session_row,
            segment_rows=segment_rows,
        )
        if not summary_text:
            return MemorySummaryGenerateResponse(created=False, summary=None)

        segment_end = int(segment_rows[-1]["sequence"])
        state_snapshot = states.get_latest_state_snapshot_before_sequence(
            session_id=session_id,
            sequence=segment_end + 1,
        )
        summary_id = new_id()
        created_at = utc_now_iso()
        summaries.create_summary(
            {
                "id": summary_id,
                "session_id": session_id,
                "segment_start": int(segment_rows[0]["sequence"]),
                "segment_end": segment_end,
                "summary": summary_text,
                "key_events": json.dumps(key_events, ensure_ascii=False),
                "state_snapshot_id": state_snapshot["id"] if state_snapshot else None,
                "frozen": 0,
                "created_at": created_at,
            }
        )
        created_row = summaries.get_summary(summary_id)
        return MemorySummaryGenerateResponse(
            created=True,
            summary=_row_to_response(created_row) if created_row is not None else None,
        )

    def list_session_summaries(self, session_id: str) -> list[MemorySummaryResponse]:
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            session_row = sessions.get_session(session_id)
            if session_row is None:
                raise NotFoundError(f"Session not found: {session_id}")
            repository = MemorySummaryRepository(connection)
            return [
                _row_to_response(row)
                for row in repository.list_by_session(session_id, limit=100)
            ]

    def list_prompt_injection_candidates(
        self,
        *,
        connection,
        session_id: str,
        before_sequence: int,
    ) -> list[MemorySummaryResponse]:
        repository = MemorySummaryRepository(connection)
        rows = repository.list_before_sequence(
            session_id,
            before_sequence=before_sequence,
            limit=get_settings().memory_prompt_summary_limit,
        )
        # Inject older -> newer for narrative continuity.
        return [_row_to_response(row) for row in reversed(rows)]
