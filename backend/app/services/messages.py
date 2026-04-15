import json

from app.core.config import get_settings
from app.core.database import get_connection
from app.core.exceptions import AppError, NotFoundError
from app.core.ids import new_id
from app.core.time import utc_now_iso
from app.repositories.cards import CardRepository
from app.repositories.messages import MessageRepository
from app.repositories.prompt_traces import PromptTraceRepository
from app.repositories.sessions import SessionRepository
from app.repositories.worldbooks import WorldBookRepository
from app.schemas.messages import (
    MessageResponse,
    MessageSwipeResponse,
    SendMessageRequest,
    SendMessageResponse,
)
from app.schemas.models import ModelChatRequest
from app.services.model_router import ModelRouterService
from app.services.prompt_pipeline import PromptPipelineService


def _simulate_assistant_reply(user_content: str, session_mode: str) -> str:
    return (
        f"[mock/{session_mode}] received: {user_content}\n\n"
        "当前链路已完成用户消息、assistant 消息、swipe 与 prompt trace 的落库。"
    )


def _swipe_row_to_response(row) -> MessageSwipeResponse:
    return MessageSwipeResponse(
        id=row["id"],
        message_id=row["message_id"],
        swipe_index=row["swipe_index"],
        generation_status=row["generation_status"],
        raw_response=row["raw_response"],
        cleaned_response=row["cleaned_response"],
        display_response=row["display_response"],
        provider_name=row["provider_name"],
        model_name=row["model_name"],
        finish_reason=row["finish_reason"],
        token_usage=json.loads(row["token_usage"]),
        trace_id=row["trace_id"],
        created_at=row["created_at"],
    )


def _message_row_to_response(row, swipes: list[MessageSwipeResponse] | None = None) -> MessageResponse:
    return MessageResponse(
        id=row["id"],
        session_id=row["session_id"],
        role=row["role"],
        sequence=row["sequence"],
        reply_to_message_id=row["reply_to_message_id"],
        content=row["content"],
        raw_content=row["raw_content"],
        structured_content=json.loads(row["structured_content"]),
        active_swipe_id=row["active_swipe_id"],
        token_count=row["token_count"],
        is_hidden=bool(row["is_hidden"]),
        is_locked=bool(row["is_locked"]),
        is_edited=bool(row["is_edited"]),
        source_type=row["source_type"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        swipes=swipes or [],
    )


class MessageService:
    def __init__(self) -> None:
        self.model_router = ModelRouterService()
        self.prompt_pipeline = PromptPipelineService()

    def list_messages(self, session_id: str) -> list[MessageResponse]:
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            session_row = sessions.get_session(session_id)
            if session_row is None:
                raise NotFoundError(f"Session not found: {session_id}")

            messages = MessageRepository(connection)
            rows = messages.list_messages_by_session(session_id)
            message_ids = [row["id"] for row in rows]
            swipe_rows = messages.list_swipes_by_message_ids(message_ids)

            swipes_by_message: dict[str, list[MessageSwipeResponse]] = {}
            for swipe_row in swipe_rows:
                swipe = _swipe_row_to_response(swipe_row)
                swipes_by_message.setdefault(swipe.message_id, []).append(swipe)

            return [
                _message_row_to_response(row, swipes_by_message.get(row["id"], []))
                for row in rows
            ]

    def send_message(self, session_id: str, payload: SendMessageRequest) -> SendMessageResponse:
        now = utc_now_iso()
        user_message_id = new_id()
        assistant_message_id = new_id()
        trace_id = new_id()
        swipe_id = new_id()

        with get_connection() as connection:
            sessions = SessionRepository(connection)
            messages = MessageRepository(connection)
            traces = PromptTraceRepository(connection)
            cards = CardRepository(connection)
            worldbooks = WorldBookRepository(connection)

            session_row = sessions.get_session(session_id)
            if session_row is None:
                raise NotFoundError(f"Session not found: {session_id}")

            last_sequence = messages.get_last_sequence(session_id)
            history_rows = messages.list_messages_by_session(session_id)
            user_sequence = last_sequence + 1
            assistant_sequence = last_sequence + 2

            user_message_values = {
                "id": user_message_id,
                "session_id": session_id,
                "role": "user",
                "sequence": user_sequence,
                "reply_to_message_id": None,
                "content": payload.content,
                "raw_content": payload.content,
                "structured_content": json.dumps(payload.structured_content, ensure_ascii=False),
                "active_swipe_id": None,
                "token_count": None,
                "is_hidden": 0,
                "is_locked": 0,
                "is_edited": 0,
                "source_type": "normal",
                "created_at": now,
                "updated_at": None,
            }
            messages.create_message(user_message_values)

            prompt_build = self.prompt_pipeline.build(
                session_row=session_row,
                history_rows=history_rows,
                current_user_input=payload.content,
                cards=cards,
                worldbooks=worldbooks,
            )
            final_messages = prompt_build.final_messages

            settings = get_settings()
            target_model = session_row["model_name"] or settings.default_chat_model

            provider_name = "mock"
            finish_reason = "stop"
            usage: dict = {}
            raw_response: dict = {}
            try:
                model_result = self.model_router.chat(
                    ModelChatRequest(
                        model_name=target_model,
                        mode=session_row["mode"],
                        messages=final_messages,
                    )
                )
                assistant_text = model_result.content
                provider_name = model_result.provider_name
                finish_reason = model_result.finish_reason or "stop"
                usage = model_result.usage
                raw_response = model_result.raw_response
            except AppError:
                if not settings.enable_mock_fallback:
                    raise
                assistant_text = _simulate_assistant_reply(
                    payload.content, session_row["mode"]
                )
                provider_name = "mock_fallback"
                raw_response = {
                    "provider": "mock_fallback",
                    "reason": "real provider unavailable",
                }

            assistant_message_values = {
                "id": assistant_message_id,
                "session_id": session_id,
                "role": "assistant",
                "sequence": assistant_sequence,
                "reply_to_message_id": user_message_id,
                "content": assistant_text,
                "raw_content": assistant_text,
                "structured_content": "[]",
                "active_swipe_id": None,
                "token_count": None,
                "is_hidden": 0,
                "is_locked": 0,
                "is_edited": 0,
                "source_type": "normal",
                "created_at": now,
                "updated_at": None,
            }
            messages.create_message(assistant_message_values)

            trace_values = {
                "id": trace_id,
                "session_id": session_id,
                "message_id": user_message_id,
                "swipe_id": None,
                "mode": session_row["mode"],
                "raw_user_input": prompt_build.raw_user_input,
                "normalized_input": prompt_build.normalized_input,
                "preset_layers": json.dumps(prompt_build.preset_layers, ensure_ascii=False),
                "injection_items": json.dumps(
                    [item.model_dump() for item in prompt_build.injection_items],
                    ensure_ascii=False,
                ),
                "final_messages": json.dumps(final_messages, ensure_ascii=False),
                "token_stats": json.dumps(usage, ensure_ascii=False),
                "tool_calls": "[]",
                "raw_response": json.dumps(raw_response, ensure_ascii=False),
                "cleaned_response": assistant_text,
                "display_response": assistant_text,
                "regex_hits": "[]",
                "state_update": "{}",
                "created_at": now,
            }
            traces.create_prompt_trace(trace_values)

            swipe_values = {
                "id": swipe_id,
                "message_id": assistant_message_id,
                "swipe_index": 0,
                "generation_status": "completed",
                "raw_response": assistant_text,
                "cleaned_response": assistant_text,
                "display_response": assistant_text,
                "provider_name": provider_name,
                "model_name": target_model,
                "finish_reason": finish_reason,
                "token_usage": json.dumps(usage, ensure_ascii=False),
                "trace_id": trace_id,
                "created_at": now,
            }
            messages.create_message_swipe(swipe_values)
            messages.update_message_active_swipe(assistant_message_id, swipe_id, now)
            traces.update_prompt_trace_swipe_id(trace_id, swipe_id)

            sessions.update_session_activity(
                session_id=session_id,
                message_count=session_row["message_count"] + 2,
                last_message_id=assistant_message_id,
                last_message_at=now,
                updated_at=now,
            )

            user_row = messages.get_message(user_message_id)
            assistant_row = messages.get_message(assistant_message_id)
            assistant_swipe_rows = messages.list_swipes_by_message_ids([assistant_message_id])

        assistant_swipes = [_swipe_row_to_response(row) for row in assistant_swipe_rows]
        return SendMessageResponse(
            user_message=_message_row_to_response(user_row),
            assistant_message=_message_row_to_response(assistant_row, assistant_swipes),
        )
