import json

from app.core.database import get_connection
from app.core.exceptions import AppError, NotFoundError
from app.core.ids import new_id
from app.core.time import utc_now_iso
from app.repositories.cards import CardRepository
from app.repositories.messages import MessageRepository
from app.repositories.play import PlayRepository
from app.repositories.prompt_traces import PromptTraceRepository
from app.repositories.quick_replies import QuickReplyRepository
from app.repositories.sessions import SessionRepository
from app.schemas.play import (
    PlayCardDetailResponse,
    PlayCardSummaryResponse,
    PlaySnapshotListResponse,
    PlayOpeningOption,
    PlayQuickReplyGroup,
    PlayQuickReplyItem,
    PlaySessionCopyRequest,
    PlaySessionCreateRequest,
    PlaySessionCreateResponse,
    PlaySessionExportResponse,
    PlaySessionOverviewResponse,
    PlaySessionRenameRequest,
    PlayStateBundleResponse,
    PlaySessionStatusRequest,
    PlayTraceListResponse,
    PlaySessionSummaryResponse,
)
from app.schemas.sessions import SessionCopyRequest, SessionCreateRequest, SessionResponse
from app.services.conversation_snapshots import ConversationSnapshotService
from app.services.prompt_traces import PromptTraceService
from app.services.sessions import SessionService, _row_to_session_response
from app.services.states import StateService


def _row_to_play_card_summary(row, opening_count: int) -> PlayCardSummaryResponse:
    return PlayCardSummaryResponse(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        tags=json.loads(row["tags_json"]) if row["tags_json"] else [],
        cover_asset_id=row["cover_asset_id"],
        avatar_asset_id=row["avatar_asset_id"],
        latest_session_id=row["latest_session_id"],
        published_at=row["published_at"],
        opening_count=opening_count,
    )


def _row_to_play_session_summary(row) -> PlaySessionSummaryResponse:
    return PlaySessionSummaryResponse(
        id=row["id"],
        name=row["name"],
        status=row["status"],
        card_id=row["card_id"],
        message_count=row["message_count"],
        last_message_id=row["last_message_id"],
        last_message_at=row["last_message_at"],
        current_state_snapshot_id=row["current_state_snapshot_id"],
        model_name=row["model_name"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class PlayService:
    def __init__(self) -> None:
        self.session_service = SessionService()
        self.state_service = StateService()
        self.prompt_trace_service = PromptTraceService()
        self.snapshot_service = ConversationSnapshotService()

    def _build_openings(self, version_row) -> list[PlayOpeningOption]:
        if version_row is None:
            return []
        prompt_blocks = json.loads(version_row["prompt_blocks"])
        openings: list[PlayOpeningOption] = []

        first_message = (prompt_blocks.get("first_mes") or "").strip()
        if first_message:
            openings.append(
                PlayOpeningOption(
                    index=0,
                    title="默认开场",
                    content=first_message,
                    is_default=True,
                )
            )

        alternate_greetings = prompt_blocks.get("alternate_greetings") or []
        for offset, item in enumerate(alternate_greetings, start=1):
            content = str(item or "").strip()
            if not content:
                continue
            openings.append(
                PlayOpeningOption(
                    index=offset,
                    title=f"备用开场 {offset}",
                    content=content,
                    is_default=False,
                )
            )
        return openings

    def list_play_cards(self) -> list[PlayCardSummaryResponse]:
        with get_connection() as connection:
            play = PlayRepository(connection)
            cards = CardRepository(connection)
            rows = play.list_published_cards()
            responses: list[PlayCardSummaryResponse] = []
            for row in rows:
                version_row = cards.get_card_version(row["current_published_version_id"])
                openings = self._build_openings(version_row)
                responses.append(_row_to_play_card_summary(row, len(openings)))
            return responses

    def get_play_card_detail(self, card_id: str) -> PlayCardDetailResponse:
        with get_connection() as connection:
            play = PlayRepository(connection)
            cards = CardRepository(connection)
            card_row = play.get_published_card(card_id)
            if card_row is None:
                raise NotFoundError(f"Published play card not found: {card_id}")
            version_row = cards.get_card_version(card_row["current_published_version_id"])
            openings = self._build_openings(version_row)
            sessions = [
                _row_to_play_session_summary(row)
                for row in play.list_play_sessions_by_card(card_id)
            ]
            return PlayCardDetailResponse(
                card=_row_to_play_card_summary(card_row, len(openings)),
                openings=openings,
                sessions=sessions[:20],
            )

    def list_play_sessions_by_card(
        self, card_id: str
    ) -> list[PlaySessionSummaryResponse]:
        with get_connection() as connection:
            play = PlayRepository(connection)
            card_row = play.get_published_card(card_id)
            if card_row is None:
                raise NotFoundError(f"Published play card not found: {card_id}")
            return [
                _row_to_play_session_summary(row)
                for row in play.list_play_sessions_by_card(card_id)
            ]

    def get_play_session_overview(self, session_id: str) -> PlaySessionOverviewResponse:
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            play = PlayRepository(connection)
            cards = CardRepository(connection)
            session_row = sessions.get_session(session_id)
            if session_row is None or session_row["mode"] != "play":
                raise NotFoundError(f"Play session not found: {session_id}")
            if not session_row["card_id"]:
                raise AppError("Play session is missing card binding.", 400)
            card_row = play.get_published_card(session_row["card_id"])
            if card_row is None:
                raise NotFoundError(
                    f"Published play card not found: {session_row['card_id']}"
                )
            version_row = cards.get_card_version(card_row["current_published_version_id"])
            openings = self._build_openings(version_row)

        current_state = self.state_service.get_current_state(session_id)
        state_summary = self.state_service.render_state_summary(
            variables=current_state.variables,
            state_schema=current_state.state_schema,
        )
        return PlaySessionOverviewResponse(
            session=_row_to_session_response(session_row),
            card=_row_to_play_card_summary(card_row, len(openings)),
            openings=openings,
            state_summary=state_summary,
        )

    def rename_play_session(
        self, session_id: str, payload: PlaySessionRenameRequest
    ) -> SessionResponse:
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            session_row = sessions.get_session(session_id)
            if session_row is None or session_row["mode"] != "play":
                raise NotFoundError(f"Play session not found: {session_id}")
            sessions.update_session_metadata(
                session_id,
                name=payload.name,
                updated_at=utc_now_iso(),
            )
            updated = sessions.get_session(session_id)
            return _row_to_session_response(updated)

    def update_play_session_status(
        self, session_id: str, payload: PlaySessionStatusRequest
    ) -> SessionResponse:
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            session_row = sessions.get_session(session_id)
            if session_row is None or session_row["mode"] != "play":
                raise NotFoundError(f"Play session not found: {session_id}")
            sessions.update_session_metadata(
                session_id,
                status=payload.status,
                updated_at=utc_now_iso(),
            )
            updated = sessions.get_session(session_id)
            return _row_to_session_response(updated)

    def copy_play_session(
        self, session_id: str, payload: PlaySessionCopyRequest
    ):
        response = self.session_service.copy_session(
            session_id,
            SessionCopyRequest(
                name=payload.name,
                source_message_id=payload.source_message_id,
            ),
        )
        session = self.session_service.get_session(response.session.id)
        if session.mode != "play":
            raise AppError("Copied session is not play mode.", 500)
        return response

    def list_quick_replies(self, session_id: str) -> list[PlayQuickReplyGroup]:
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            quick_replies = QuickReplyRepository(connection)
            session_row = sessions.get_session(session_id)
            if session_row is None or session_row["mode"] != "play":
                raise NotFoundError(f"Play session not found: {session_id}")

            groups: list[PlayQuickReplyGroup] = []
            for row in quick_replies.list_global_sets():
                groups.append(self._row_to_quick_reply_group(row))
            if session_row["card_id"]:
                for row in quick_replies.list_card_sets(session_row["card_id"]):
                    groups.append(self._row_to_quick_reply_group(row))
            return groups

    def _row_to_quick_reply_group(self, row) -> PlayQuickReplyGroup:
        raw_items = json.loads(row["items"]) if row["items"] else []
        items: list[PlayQuickReplyItem] = []
        for index, item in enumerate(raw_items):
            if isinstance(item, str):
                items.append(
                    PlayQuickReplyItem(
                        id=f"{row['id']}#{index}",
                        label=item,
                        content=item,
                        order=index,
                    )
                )
                continue
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or item.get("title") or item.get("name") or f"Quick Reply {index + 1}")
            content = str(item.get("content") or item.get("text") or item.get("value") or "")
            if not content.strip():
                continue
            items.append(
                PlayQuickReplyItem(
                    id=str(item.get("id") or f"{row['id']}#{index}"),
                    label=label,
                    content=content,
                    mode=str(item.get("mode") or "fill"),
                    order=int(item.get("order") or index),
                )
            )
        return PlayQuickReplyGroup(
            id=row["id"],
            name=row["name"],
            scope_type=row["scope_type"],
            items=items,
        )

    def export_play_session(
        self,
        session_id: str,
        *,
        export_format: str,
        export_scope: str,
    ) -> PlaySessionExportResponse:
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            messages = MessageRepository(connection)
            session_row = sessions.get_session(session_id)
            if session_row is None or session_row["mode"] != "play":
                raise NotFoundError(f"Play session not found: {session_id}")
            visible_rows = messages.list_messages_by_session(session_id)

        file_ext = "md" if export_format == "markdown" else "txt"
        safe_name = session_row["name"].replace("/", "_").replace("\\", "_")
        file_name = f"{safe_name}.{file_ext}"
        if export_scope == "reader":
            content = self._render_reader_export(
                session_name=session_row["name"],
                messages=visible_rows,
                markdown=export_format == "markdown",
            )
        elif export_scope == "debug":
            content = self._render_debug_export(
                session_id=session_id,
                session_name=session_row["name"],
                messages=visible_rows,
                markdown=export_format == "markdown",
            )
        else:
            raise AppError(f"Unsupported export_scope: {export_scope}", 400)

        return PlaySessionExportResponse(
            session_id=session_id,
            export_format=export_format,
            export_scope=export_scope,
            file_name=file_name,
            content=content,
        )

    def list_play_snapshots(self, session_id: str) -> PlaySnapshotListResponse:
        overview = self.get_play_session_overview(session_id)
        items = self.snapshot_service.list_snapshots(overview.session.id)
        return PlaySnapshotListResponse(items=items)

    def restore_play_snapshot(self, session_id: str, snapshot_id: str):
        self.get_play_session_overview(session_id)
        return self.snapshot_service.restore_snapshot(
            session_id=session_id,
            snapshot_id=snapshot_id,
        )

    def get_play_state_bundle(self, session_id: str) -> PlayStateBundleResponse:
        self.get_play_session_overview(session_id)
        return PlayStateBundleResponse(
            current=self.state_service.get_current_state(session_id),
            snapshots=self.state_service.list_state_snapshots(session_id),
            changes=self.state_service.list_state_change_logs(session_id),
        )

    def list_play_traces(self, session_id: str) -> PlayTraceListResponse:
        self.get_play_session_overview(session_id)
        return PlayTraceListResponse(
            items=self.prompt_trace_service.list_session_traces(session_id)
        )

    def get_latest_play_trace(self, session_id: str):
        self.get_play_session_overview(session_id)
        return self.prompt_trace_service.get_latest_trace_by_session(session_id)

    def get_play_trace(self, session_id: str, trace_id: str):
        self.get_play_session_overview(session_id)
        trace = self.prompt_trace_service.get_trace(trace_id)
        if trace.session_id != session_id:
            raise NotFoundError(f"Prompt trace not found in play session: {trace_id}")
        return trace

    def get_play_trace_by_message(self, session_id: str, message_id: str):
        self.get_play_session_overview(session_id)
        trace = self.prompt_trace_service.get_latest_trace_by_message(message_id)
        if trace.session_id != session_id:
            raise NotFoundError(
                f"Prompt trace not found for message in play session: {message_id}"
            )
        return trace

    def _render_reader_export(self, *, session_name: str, messages: list, markdown: bool) -> str:
        lines: list[str] = []
        if markdown:
            lines.append(f"# {session_name}")
            lines.append("")
        else:
            lines.append(session_name)
            lines.append("=" * len(session_name))
            lines.append("")

        for row in messages:
            role = "用户" if row["role"] == "user" else "角色"
            if markdown:
                lines.append(f"## {role}")
                lines.append(row["content"])
                lines.append("")
            else:
                lines.append(f"[{role}]")
                lines.append(row["content"])
                lines.append("")
        return "\n".join(lines).strip()

    def _render_debug_export(
        self, *, session_id: str, session_name: str, messages: list, markdown: bool
    ) -> str:
        traces = self.prompt_trace_service.list_session_traces(session_id)
        current_state = self.state_service.get_current_state(session_id)
        state_summary = self.state_service.render_state_summary(
            variables=current_state.variables,
            state_schema=current_state.state_schema,
        )
        lines: list[str] = []
        if markdown:
            lines.append(f"# {session_name}")
            lines.append("")
            lines.append("## 当前状态")
            lines.append(state_summary or "无")
            lines.append("")
            lines.append("## 消息")
        else:
            lines.append(session_name)
            lines.append("=" * len(session_name))
            lines.append("")
            lines.append("[当前状态]")
            lines.append(state_summary or "无")
            lines.append("")
            lines.append("[消息]")

        for row in messages:
            role = "user" if row["role"] == "user" else row["role"]
            lines.append(f"- #{row['sequence']} {role}: {row['content']}")

        lines.append("" if markdown else "")
        lines.append("## Prompt Trace 摘要" if markdown else "[Prompt Trace 摘要]")
        for trace in traces[:20]:
            lines.append(
                f"- trace={trace.id} message={trace.message_id} mode={trace.mode} created_at={trace.created_at}"
            )
        return "\n".join(lines).strip()

    def create_play_session(
        self, card_id: str, payload: PlaySessionCreateRequest
    ) -> PlaySessionCreateResponse:
        with get_connection() as connection:
            play = PlayRepository(connection)
            cards = CardRepository(connection)
            messages = MessageRepository(connection)
            sessions = SessionRepository(connection)

            card_row = play.get_published_card(card_id)
            if card_row is None:
                raise NotFoundError(f"Published play card not found: {card_id}")

            existing_sessions = play.list_play_sessions_by_card(card_id)
            if payload.use_latest_existing_session and existing_sessions:
                latest = existing_sessions[0]
                session_row = sessions.get_session(latest["id"])
                return PlaySessionCreateResponse(
                    session=_row_to_session_response(session_row),
                    opening_message_id=None,
                    opening_selected=None,
                )

            version_row = cards.get_card_version(card_row["current_published_version_id"])
            openings = self._build_openings(version_row)
            selected_opening = None
            if payload.opening_index is not None:
                selected_opening = next(
                    (item for item in openings if item.index == payload.opening_index),
                    None,
                )
                if selected_opening is None:
                    raise AppError("Selected opening_index does not exist.", 400)
            elif openings:
                selected_opening = openings[0]

            create_payload = SessionCreateRequest(
                mode="play",
                name=payload.name,
                status="active",
                card_id=card_id,
                card_version_id=card_row["current_published_version_id"],
                worldbook_id=None,
                model_name=payload.model_name,
            )
            now = utc_now_iso()
            session_id = new_id()

            session_row = self.session_service._create_session_record(
                sessions=sessions,
                cards=cards,
                payload=create_payload,
                now=now,
                session_id=session_id,
            )
            opening_message_id = None
            if selected_opening is not None:
                opening_message_id = new_id()
                messages.create_message(
                    {
                        "id": opening_message_id,
                        "session_id": session_id,
                        "role": "assistant",
                        "sequence": 1,
                        "reply_to_message_id": None,
                        "content": selected_opening.content,
                        "raw_content": selected_opening.content,
                        "structured_content": "[]",
                        "active_swipe_id": None,
                        "token_count": None,
                        "is_hidden": 0,
                        "is_locked": 0,
                        "is_edited": 0,
                        "source_type": "opening",
                        "created_at": now,
                        "updated_at": None,
                    }
                )
                sessions.update_session_activity(
                    session_id=session_id,
                    message_count=1,
                    last_message_id=opening_message_id,
                    last_message_at=now,
                    updated_at=now,
                )
                session_row = sessions.get_session(session_id)

        self.state_service.initialize_session_state(session_id)
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            session_row = sessions.get_session(session_id)
            if session_row is None:
                raise NotFoundError(f"Session not found: {session_id}")
            return PlaySessionCreateResponse(
                session=_row_to_session_response(session_row),
                opening_message_id=opening_message_id,
                opening_selected=selected_opening,
            )
