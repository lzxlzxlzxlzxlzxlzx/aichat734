import json

from app.core.config import get_settings
from app.core.database import get_connection
from app.core.exceptions import NotFoundError
from app.core.time import utc_now_iso
from app.repositories.chat import ChatRepository
from app.repositories.prompt_traces import PromptTraceRepository
from app.repositories.quick_replies import QuickReplyRepository
from app.repositories.sessions import SessionRepository
from app.schemas.chat import (
    ChatAssistantProfileResponse,
    ChatQuickReplyGroup,
    ChatQuickReplyItem,
    ChatRecentCardSummaryResponse,
    ChatSessionModelRequest,
    ChatSessionCreateRequest,
    ChatSessionOverviewResponse,
    ChatSessionRenameRequest,
    ChatSessionStatusRequest,
    ChatSessionSummaryResponse,
    ChatTraceListResponse,
)
from app.schemas.sessions import SessionCreateRequest, SessionResponse
from app.services.prompt_traces import PromptTraceService, _row_to_summary
from app.services.sessions import SessionService, _row_to_session_response


DEFAULT_CHAT_SESSION_NAME = "新聊天"

KONATA_ASSISTANT_PROFILE = ChatAssistantProfileResponse(
    name="泉此方",
    title="聊天模式常驻助手人格",
    summary=(
        "以泉此方风格常驻聊天模式。整体表达轻松、敏锐、会接梗，也能认真讨论项目、角色卡、"
        "世界书与剧情设计；在聊天模式下她不是可切换角色卡，而是长期对话的人格底座。"
    ),
    traits=[
        "轻松自然",
        "有梗但不过度表演",
        "能聊日常，也能聊创作",
        "保持长期对话连续性",
    ],
)


def _row_to_chat_session_summary(row) -> ChatSessionSummaryResponse:
    return ChatSessionSummaryResponse(
        id=row["id"],
        name=row["name"],
        status=row["status"],
        message_count=row["message_count"],
        last_message_id=row["last_message_id"],
        last_message_at=row["last_message_at"],
        model_name=row["model_name"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_recent_card_summary(row) -> ChatRecentCardSummaryResponse:
    return ChatRecentCardSummaryResponse(
        id=row["id"],
        name=row["name"],
        description=row["description"] or "",
        tags=json.loads(row["tags_json"]) if row["tags_json"] else [],
        cover_asset_id=row["cover_asset_id"],
        avatar_asset_id=row["avatar_asset_id"],
        latest_session_id=row["latest_session_id"],
        last_interaction_at=row["last_interaction_at"],
    )


class ChatService:
    def __init__(self) -> None:
        self.session_service = SessionService()
        self.prompt_trace_service = PromptTraceService()

    def _require_chat_session(self, session_id: str):
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            session_row = sessions.get_session(session_id)
            if session_row is None or session_row["mode"] != "chat":
                raise NotFoundError(f"Chat session not found: {session_id}")
            return session_row

    def list_chat_sessions(self) -> list[ChatSessionSummaryResponse]:
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            rows = sessions.list_sessions_by_mode("chat")
            return [_row_to_chat_session_summary(row) for row in rows]

    def create_chat_session(
        self, payload: ChatSessionCreateRequest
    ) -> SessionResponse:
        settings = get_settings()
        create_payload = SessionCreateRequest(
            mode="chat",
            name=(payload.name or DEFAULT_CHAT_SESSION_NAME).strip() or DEFAULT_CHAT_SESSION_NAME,
            status="active",
            model_name=payload.model_name or settings.default_chat_model,
        )
        return self.session_service.create_session(create_payload)

    def rename_chat_session(
        self, session_id: str, payload: ChatSessionRenameRequest
    ) -> SessionResponse:
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            session_row = sessions.get_session(session_id)
            if session_row is None or session_row["mode"] != "chat":
                raise NotFoundError(f"Chat session not found: {session_id}")
            sessions.update_session_metadata(
                session_id,
                name=payload.name,
                updated_at=utc_now_iso(),
            )
            updated = sessions.get_session(session_id)
            return _row_to_session_response(updated)

    def update_chat_session_status(
        self, session_id: str, payload: ChatSessionStatusRequest
    ) -> SessionResponse:
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            session_row = sessions.get_session(session_id)
            if session_row is None or session_row["mode"] != "chat":
                raise NotFoundError(f"Chat session not found: {session_id}")
            sessions.update_session_metadata(
                session_id,
                status=payload.status,
                updated_at=utc_now_iso(),
            )
            updated = sessions.get_session(session_id)
            return _row_to_session_response(updated)

    def update_chat_session_model(
        self, session_id: str, payload: ChatSessionModelRequest
    ) -> SessionResponse:
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            session_row = sessions.get_session(session_id)
            if session_row is None or session_row["mode"] != "chat":
                raise NotFoundError(f"Chat session not found: {session_id}")
            sessions.update_session_metadata(
                session_id,
                model_name=payload.model_name.strip(),
                updated_at=utc_now_iso(),
            )
            updated = sessions.get_session(session_id)
            return _row_to_session_response(updated)

    def list_quick_replies(self, session_id: str) -> list[ChatQuickReplyGroup]:
        self._require_chat_session(session_id)
        with get_connection() as connection:
            quick_replies = QuickReplyRepository(connection)
            return [self._row_to_quick_reply_group(row) for row in quick_replies.list_global_sets()]

    def _row_to_quick_reply_group(self, row) -> ChatQuickReplyGroup:
        raw_items = json.loads(row["items"]) if row["items"] else []
        items: list[ChatQuickReplyItem] = []
        for index, item in enumerate(raw_items):
            if isinstance(item, str):
                items.append(
                    ChatQuickReplyItem(
                        id=f"{row['id']}#{index}",
                        label=item,
                        content=item,
                        order=index,
                    )
                )
                continue
            if not isinstance(item, dict):
                continue
            content = str(item.get("content") or item.get("text") or item.get("value") or "")
            if not content.strip():
                continue
            items.append(
                ChatQuickReplyItem(
                    id=str(item.get("id") or f"{row['id']}#{index}"),
                    label=str(item.get("label") or item.get("title") or item.get("name") or f"Quick Reply {index + 1}"),
                    content=content,
                    mode=str(item.get("mode") or "fill"),
                    order=int(item.get("order") or index),
                )
            )
        return ChatQuickReplyGroup(
            id=row["id"],
            name=row["name"],
            scope_type=row["scope_type"],
            items=items,
        )

    def list_recent_cards(self, limit: int = 8) -> list[ChatRecentCardSummaryResponse]:
        with get_connection() as connection:
            chat_repository = ChatRepository(connection)
            rows = chat_repository.list_recent_cards(limit=limit)
            return [_row_to_recent_card_summary(row) for row in rows]

    def get_chat_session_overview(self, session_id: str) -> ChatSessionOverviewResponse:
        session = self._require_chat_session(session_id)
        quick_replies = self.list_quick_replies(session_id)
        recent_cards = self.list_recent_cards()

        latest_trace = None
        with get_connection() as connection:
            traces = PromptTraceRepository(connection)
            rows = traces.list_by_session(session_id)
            if rows:
                latest_trace = _row_to_summary(rows[0])

        return ChatSessionOverviewResponse(
            session=_row_to_session_response(session),
            assistant_profile=KONATA_ASSISTANT_PROFILE,
            quick_replies=quick_replies,
            recent_cards=recent_cards,
            latest_trace=latest_trace,
        )

    def list_chat_traces(self, session_id: str) -> ChatTraceListResponse:
        self._require_chat_session(session_id)
        return ChatTraceListResponse(
            items=self.prompt_trace_service.list_session_traces(session_id)
        )

    def get_latest_chat_trace(self, session_id: str):
        self._require_chat_session(session_id)
        return self.prompt_trace_service.get_latest_trace_by_session(session_id)

    def get_chat_trace(self, session_id: str, trace_id: str):
        self._require_chat_session(session_id)
        trace = self.prompt_trace_service.get_trace(trace_id)
        if trace.session_id != session_id:
            raise NotFoundError(f"Prompt trace not found in chat session: {trace_id}")
        return trace

    def get_chat_trace_by_message(self, session_id: str, message_id: str):
        self._require_chat_session(session_id)
        trace = self.prompt_trace_service.get_latest_trace_by_message(message_id)
        if trace.session_id != session_id:
            raise NotFoundError(
                f"Prompt trace not found for message in chat session: {message_id}"
            )
        return trace
