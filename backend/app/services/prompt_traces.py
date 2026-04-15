import json

from app.core.database import get_connection
from app.core.exceptions import NotFoundError
from app.repositories.prompt_traces import PromptTraceRepository
from app.repositories.sessions import SessionRepository
from app.schemas.prompt_traces import (
    PromptTraceFinalMessagesSection,
    PromptTraceInjectionSection,
    PromptTraceInputSection,
    PromptTraceInspectorResponse,
    PromptTraceOverviewSection,
    PromptTracePresetSection,
    PromptTraceResponseSection,
    PromptTraceSummaryResponse,
    PromptTraceTokenSection,
)


def _safe_json_loads(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if value == "":
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _row_to_summary(row) -> PromptTraceSummaryResponse:
    return PromptTraceSummaryResponse(
        id=row["id"],
        session_id=row["session_id"],
        message_id=row["message_id"],
        swipe_id=row["swipe_id"],
        mode=row["mode"],
        created_at=row["created_at"],
    )


def _group_items(items: list[dict], key: str) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for item in items:
        group_key = str(item.get(key) or "unknown")
        grouped.setdefault(group_key, []).append(item)
    return grouped


def _build_role_counts(final_messages: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in final_messages:
        role = str(item.get("role") or "unknown")
        counts[role] = counts.get(role, 0) + 1
    return counts


def _read_estimated_output(token_stats: dict, display_response: str | None) -> int | None:
    for key in ("estimated_output", "output_tokens", "completion_tokens"):
        value = token_stats.get(key)
        if isinstance(value, int):
            return value
    if display_response:
        return max(1, len(display_response) // 4)
    return None


def _row_to_inspector(row) -> PromptTraceInspectorResponse:
    preset_layers = _safe_json_loads(row["preset_layers"]) or {}
    injection_items = _safe_json_loads(row["injection_items"]) or []
    final_messages = _safe_json_loads(row["final_messages"]) or []
    tool_calls = _safe_json_loads(row["tool_calls"]) or []
    token_stats = _safe_json_loads(row["token_stats"]) or {}
    raw_response = _safe_json_loads(row["raw_response"])
    regex_hits = _safe_json_loads(row["regex_hits"]) or []
    state_update = _safe_json_loads(row["state_update"]) or {}
    raw_user_input = row["raw_user_input"]
    normalized_input = row["normalized_input"]
    cleaned_response = row["cleaned_response"]
    display_response = row["display_response"]

    estimated_input = token_stats.get("estimated_input")
    if not isinstance(estimated_input, int):
        estimated_input = sum(
            int(item.get("token_estimate") or 0) for item in injection_items
        )

    estimated_output = _read_estimated_output(token_stats, display_response)
    estimated_total = (
        estimated_input + estimated_output
        if isinstance(estimated_input, int) and isinstance(estimated_output, int)
        else None
    )

    preset_section = PromptTracePresetSection(
        global_core=preset_layers.get("global_core") or [],
        mode_specific=preset_layers.get("mode_specific") or [],
        izumi_persona=preset_layers.get("izumi_persona") or [],
        st_compat_legacy=preset_layers.get("st_compat_legacy") or [],
    )
    preset_section.total_items = (
        len(preset_section.global_core)
        + len(preset_section.mode_specific)
        + len(preset_section.izumi_persona)
        + len(preset_section.st_compat_legacy)
    )

    state_update_parsed = state_update.get("parsed") if isinstance(state_update, dict) else None
    has_state_update = bool(
        state_update
        and (
            state_update.get("raw_block")
            or (isinstance(state_update_parsed, dict) and state_update_parsed)
        )
    )

    return PromptTraceInspectorResponse(
        id=row["id"],
        session_id=row["session_id"],
        message_id=row["message_id"],
        swipe_id=row["swipe_id"],
        mode=row["mode"],
        raw_user_input=raw_user_input,
        normalized_input=normalized_input,
        preset_layers=preset_layers,
        injection_items=injection_items,
        final_messages=final_messages,
        tool_calls=tool_calls,
        token_stats=token_stats,
        raw_response=raw_response,
        cleaned_response=cleaned_response,
        display_response=display_response,
        regex_hits=regex_hits,
        state_update=state_update,
        injection_count=len(injection_items),
        final_message_count=len(final_messages),
        input_section=PromptTraceInputSection(
            raw_user_input=raw_user_input,
            normalized_input=normalized_input,
            raw_length=len(raw_user_input or ""),
            normalized_length=len(normalized_input or ""),
        ),
        preset_section=preset_section,
        injection_section=PromptTraceInjectionSection(
            items=injection_items,
            by_stage=_group_items(injection_items, "stage"),
            by_source_type=_group_items(injection_items, "source_type"),
            total_items=len(injection_items),
            total_token_estimate=sum(
                int(item.get("token_estimate") or 0) for item in injection_items
            ),
        ),
        final_messages_section=PromptTraceFinalMessagesSection(
            messages=final_messages,
            role_counts=_build_role_counts(final_messages),
            total_messages=len(final_messages),
        ),
        response_section=PromptTraceResponseSection(
            raw_response=raw_response,
            cleaned_response=cleaned_response,
            display_response=display_response,
            cleaned_length=len(cleaned_response or ""),
            display_length=len(display_response or ""),
        ),
        token_section=PromptTraceTokenSection(
            stats=token_stats,
            estimated_input=estimated_input,
            estimated_output=estimated_output,
            estimated_total=estimated_total,
        ),
        overview=PromptTraceOverviewSection(
            has_tool_calls=bool(tool_calls),
            has_regex_hits=bool(regex_hits),
            has_state_update=has_state_update,
            tool_call_count=len(tool_calls),
            regex_hit_count=len(regex_hits),
        ),
        created_at=row["created_at"],
    )


class PromptTraceService:
    def list_session_traces(self, session_id: str) -> list[PromptTraceSummaryResponse]:
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            session = sessions.get_session(session_id)
            if session is None:
                raise NotFoundError(f"Session not found: {session_id}")

            repository = PromptTraceRepository(connection)
            rows = repository.list_by_session(session_id)
            return [_row_to_summary(row) for row in rows]

    def get_trace(self, trace_id: str) -> PromptTraceInspectorResponse:
        with get_connection() as connection:
            repository = PromptTraceRepository(connection)
            row = repository.get_by_id(trace_id)
            if row is None:
                raise NotFoundError(f"Prompt trace not found: {trace_id}")
            return _row_to_inspector(row)

    def get_latest_trace_by_message(self, message_id: str) -> PromptTraceInspectorResponse:
        with get_connection() as connection:
            repository = PromptTraceRepository(connection)
            row = repository.get_latest_by_message_id(message_id)
            if row is None:
                raise NotFoundError(
                    f"Prompt trace not found for message: {message_id}"
                )
            return _row_to_inspector(row)

    def get_latest_trace_by_session(self, session_id: str) -> PromptTraceInspectorResponse:
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            session = sessions.get_session(session_id)
            if session is None:
                raise NotFoundError(f"Session not found: {session_id}")

            repository = PromptTraceRepository(connection)
            rows = repository.list_by_session(session_id)
            if not rows:
                raise NotFoundError(f"Prompt trace not found for session: {session_id}")
            return self.get_trace(rows[0]["id"])
