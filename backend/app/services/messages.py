import json

from app.core.config import get_settings
from app.core.database import get_connection
from app.core.exceptions import AppError, NotFoundError
from app.core.ids import new_id
from app.core.time import utc_now_iso
from app.repositories.cards import CardRepository
from app.repositories.media import MediaRepository
from app.repositories.messages import MessageRepository
from app.repositories.prompt_traces import PromptTraceRepository
from app.repositories.sessions import SessionRepository
from app.repositories.worldbooks import WorldBookRepository
from app.schemas.messages import (
    DeleteSwipeResponse,
    MessageReferenceRequest,
    MessageResponse,
    MessageSwipeResponse,
    RegenerateMessageRequest,
    RollbackResponse,
    SendMessageRequest,
    SendMessageResponse,
    ToggleMessageLockRequest,
    UpdateMessageResponse,
    UpdateMessageRequest,
)
from app.schemas.models import ModelChatRequest
from app.schemas.media import MessageAttachmentResponse
from app.schemas.prompt_pipeline import PromptInjectionItem
from app.services.model_router import ModelRouterService
from app.services.long_term_memories import LongTermMemoryService
from app.services.memory_summaries import MemorySummaryService
from app.services.prompt_pipeline import PromptPipelineService
from app.services.conversation_snapshots import ConversationSnapshotService
from app.services.media import _row_to_media_asset_response
from app.services.states import StateService


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
        attachments=[],
    )


def _attachment_row_to_response(row) -> MessageAttachmentResponse:
    return MessageAttachmentResponse(
        id=row["id"],
        message_id=row["message_id"],
        media_asset_id=row["media_asset_id"],
        attachment_type=row["attachment_type"],
        order_index=row["order_index"],
        caption=row["caption"],
        created_at=row["attachment_created_at"],
        asset=_row_to_media_asset_response(row),
    )


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


class MessageService:
    def __init__(self) -> None:
        self.model_router = ModelRouterService()
        self.long_term_memory_service = LongTermMemoryService()
        self.memory_summary_service = MemorySummaryService()
        self.prompt_pipeline = PromptPipelineService()
        self.state_service = StateService()
        self.snapshot_service = ConversationSnapshotService()

    def _get_message_with_swipes(
        self,
        *,
        connection,
        message_id: str,
    ) -> MessageResponse:
        messages = MessageRepository(connection)
        media = MediaRepository(connection)
        row = messages.get_message(message_id)
        if row is None or bool(row["is_hidden"]):
            raise NotFoundError(f"Message not found: {message_id}")
        swipe_rows = messages.list_swipes_by_message_ids([message_id])
        swipes = [_swipe_row_to_response(swipe_row) for swipe_row in swipe_rows]
        attachment_rows = media.list_attachments_by_message_ids([message_id])
        response = _message_row_to_response(row, swipes)
        response.attachments = [
            _attachment_row_to_response(attachment_row)
            for attachment_row in attachment_rows
        ]
        return response

    def _bind_message_attachments(
        self,
        *,
        connection,
        message_id: str,
        attachments,
        now: str,
    ) -> None:
        if not attachments:
            return
        media = MediaRepository(connection)
        for index, attachment in enumerate(attachments):
            asset_row = media.get_media_asset(attachment.media_asset_id)
            if asset_row is None:
                raise NotFoundError(
                    f"Media asset not found: {attachment.media_asset_id}"
                )
            media.create_message_attachment(
                {
                    "id": new_id(),
                    "message_id": message_id,
                    "media_asset_id": attachment.media_asset_id,
                    "attachment_type": attachment.attachment_type,
                    "order_index": (
                        attachment.order_index
                        if attachment.order_index is not None
                        else index
                    ),
                    "caption": attachment.caption,
                    "created_at": now,
                }
            )

    def _replace_message_attachments(
        self,
        *,
        connection,
        message_id: str,
        attachments,
        now: str,
    ) -> None:
        media = MediaRepository(connection)
        media.delete_attachments_by_message_id(message_id)
        self._bind_message_attachments(
            connection=connection,
            message_id=message_id,
            attachments=attachments,
            now=now,
        )

    def _build_reference_structured_content(
        self,
        *,
        structured_content: list[dict] | list,
        references: list[MessageReferenceRequest],
    ) -> list[dict] | list:
        normalized = list(structured_content or [])
        if not references:
            return normalized
        normalized.append(
            {
                "type": "chat_references",
                "items": [reference.model_dump() for reference in references],
            }
        )
        return normalized

    def _extract_reference_requests(
        self, structured_content: list[dict] | list
    ) -> list[MessageReferenceRequest]:
        references: list[MessageReferenceRequest] = []
        for block in structured_content or []:
            if not isinstance(block, dict):
                continue
            if block.get("type") != "chat_references":
                continue
            items = block.get("items") or []
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                try:
                    references.append(MessageReferenceRequest.model_validate(item))
                except Exception:
                    continue
        return references

    def _make_reference_item(
        self,
        *,
        reference_type: str,
        target_id: str,
        label: str,
        content: str,
        mode: str,
        priority: int = 700,
    ) -> PromptInjectionItem:
        return PromptInjectionItem(
            id=new_id(),
            source_type=f"chat_reference_{reference_type}",
            source_id=target_id,
            label=label,
            content=content,
            stage="before_history",
            priority=priority,
            token_estimate=_estimate_tokens(content),
            mode=mode,
        )

    def _format_session_reference_content(self, *, session_row, message_rows: list) -> str:
        transcript_lines = [
            f"Referenced session: {session_row['name']}",
            f"Mode: {session_row['mode']}",
            "Transcript snippet:",
        ]
        for row in message_rows:
            transcript_lines.append(f"{row['role']}: {row['content']}")
        return "\n".join(transcript_lines)

    def _resolve_reference_items(
        self,
        *,
        connection,
        session_row,
        references: list[MessageReferenceRequest],
    ) -> list[PromptInjectionItem]:
        if not references:
            return []

        cards = CardRepository(connection)
        worldbooks = WorldBookRepository(connection)
        sessions = SessionRepository(connection)
        messages = MessageRepository(connection)
        items: list[PromptInjectionItem] = []

        for reference in references:
            label = reference.label or reference.target_id
            if reference.reference_type == "card":
                card_row = cards.get_card(reference.target_id)
                if card_row is None:
                    items.append(
                        self._make_reference_item(
                            reference_type="missing",
                            target_id=reference.target_id,
                            label=f"Unavailable Card Reference: {label}",
                            content=f"Requested card reference is unavailable: {reference.target_id}",
                            mode=session_row["mode"],
                            priority=300,
                        )
                    )
                    continue
                version_id = (
                    card_row["current_published_version_id"]
                    or card_row["current_draft_version_id"]
                )
                version_row = cards.get_card_version(version_id) if version_id else None
                prompt_blocks = (
                    json.loads(version_row["prompt_blocks"])
                    if version_row is not None and version_row["prompt_blocks"]
                    else {}
                )
                content = "\n".join(
                    [
                        f"Referenced character card: {card_row['name']}",
                        f"Description: {card_row['description'] or ''}",
                        f"Scenario: {prompt_blocks.get('scenario', '')}",
                        f"Personality: {prompt_blocks.get('personality', '')}",
                        f"Speaking style: {prompt_blocks.get('speaking_style', '')}",
                        f"Background: {prompt_blocks.get('background', '')}",
                    ]
                ).strip()
                items.append(
                    self._make_reference_item(
                        reference_type="card",
                        target_id=reference.target_id,
                        label=f"Referenced Card: {card_row['name']}",
                        content=content,
                        mode=session_row["mode"],
                    )
                )
                continue

            if reference.reference_type == "worldbook":
                worldbook_row = worldbooks.get_worldbook(reference.target_id)
                if worldbook_row is None:
                    items.append(
                        self._make_reference_item(
                            reference_type="missing",
                            target_id=reference.target_id,
                            label=f"Unavailable WorldBook Reference: {label}",
                            content=f"Requested worldbook reference is unavailable: {reference.target_id}",
                            mode=session_row["mode"],
                            priority=300,
                        )
                    )
                    continue
                entry_rows = worldbooks.list_constant_entries(reference.target_id)
                entry_lines = [
                    f"- {entry['title']}: {entry['content']}"
                    for entry in entry_rows[:8]
                ]
                content = "\n".join(
                    [
                        f"Referenced worldbook: {worldbook_row['name']}",
                        f"Description: {worldbook_row['description'] or ''}",
                        "Constant entries:",
                        *entry_lines,
                    ]
                )
                items.append(
                    self._make_reference_item(
                        reference_type="worldbook",
                        target_id=reference.target_id,
                        label=f"Referenced WorldBook: {worldbook_row['name']}",
                        content=content,
                        mode=session_row["mode"],
                    )
                )
                continue

            if reference.reference_type == "session":
                referenced_session = sessions.get_session(reference.target_id)
                if referenced_session is None:
                    items.append(
                        self._make_reference_item(
                            reference_type="missing",
                            target_id=reference.target_id,
                            label=f"Unavailable Session Reference: {label}",
                            content=f"Requested session reference is unavailable: {reference.target_id}",
                            mode=session_row["mode"],
                            priority=300,
                        )
                    )
                    continue
                all_rows = messages.list_messages_by_session(reference.target_id)
                limit = reference.max_messages or 6
                snippet_rows = all_rows[-limit:]
                items.append(
                    self._make_reference_item(
                        reference_type="session",
                        target_id=reference.target_id,
                        label=f"Referenced Session: {referenced_session['name']}",
                        content=self._format_session_reference_content(
                            session_row=referenced_session,
                            message_rows=snippet_rows,
                        ),
                        mode=session_row["mode"],
                    )
                )
                continue

            message_row = messages.get_message(reference.target_id)
            if message_row is None:
                items.append(
                    self._make_reference_item(
                        reference_type="missing",
                        target_id=reference.target_id,
                        label=f"Unavailable Message Reference: {label}",
                        content=f"Requested message reference is unavailable: {reference.target_id}",
                        mode=session_row["mode"],
                        priority=300,
                    )
                )
                continue
            source_session = sessions.get_session(message_row["session_id"])
            source_name = source_session["name"] if source_session is not None else message_row["session_id"]
            content = "\n".join(
                [
                    f"Referenced message from session: {source_name}",
                    f"Role: {message_row['role']}",
                    f"Content: {message_row['content']}",
                ]
            )
            items.append(
                self._make_reference_item(
                    reference_type="message",
                    target_id=reference.target_id,
                    label=f"Referenced Message: {label}",
                    content=content,
                    mode=session_row["mode"],
                )
            )

        return items

    def _maybe_auto_rename_chat_session(
        self,
        *,
        connection,
        session_row,
        history_rows: list,
        first_user_message: str,
        now: str,
    ) -> None:
        if session_row["mode"] != "chat" or history_rows:
            return
        current_name = (session_row["name"] or "").strip()
        if current_name and current_name != "新聊天":
            return

        normalized = " ".join(first_user_message.strip().split())
        if not normalized:
            return
        generated_name = normalized[:24].rstrip("，。！？,.!?:; ")
        if not generated_name:
            return
        SessionRepository(connection).update_session_metadata(
            session_row["id"],
            name=generated_name,
            updated_at=now,
        )

    def _build_prompt_for_user_message(
        self,
        *,
        session_row,
        user_message_row,
        connection,
    ):
        messages = MessageRepository(connection)
        media = MediaRepository(connection)
        cards = CardRepository(connection)
        worldbooks = WorldBookRepository(connection)
        history_rows = messages.list_messages_before_sequence(
            session_row["id"], user_message_row["sequence"]
        )
        attachment_rows = media.list_attachments_by_message_ids([user_message_row["id"]])
        structured_content = json.loads(user_message_row["structured_content"])
        references = self._extract_reference_requests(structured_content)
        reference_items = self._resolve_reference_items(
            connection=connection,
            session_row=session_row,
            references=references,
        )
        return self.prompt_pipeline.build(
            session_row=session_row,
            history_rows=history_rows,
            current_user_input=user_message_row["content"],
            current_attachment_rows=attachment_rows,
            cards=cards,
            worldbooks=worldbooks,
            extra_injection_items=reference_items,
        )

    def _generate_model_reply(
        self,
        *,
        session_row,
        final_messages: list[dict],
        fallback_user_content: str,
        model_name_override: str | None = None,
    ) -> tuple[str, str, str, dict, dict, str]:
        settings = get_settings()
        target_model = model_name_override or session_row["model_name"] or settings.default_chat_model
        provider_name = "mock"
        finish_reason = "stop"
        usage: dict = {}
        raw_provider_response: dict = {}
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
            raw_provider_response = model_result.raw_response
        except AppError:
            if not settings.enable_mock_fallback:
                raise
            assistant_text = _simulate_assistant_reply(
                fallback_user_content, session_row["mode"]
            )
            provider_name = "mock_fallback"
            raw_provider_response = {
                "provider": "mock_fallback",
                "reason": "real provider unavailable",
            }
        return target_model, provider_name, finish_reason, usage, raw_provider_response, assistant_text

    def _capture_state_snapshot_id(self, session_row) -> str | None:
        return session_row["current_state_snapshot_id"]

    def _create_edit_cutoff_snapshot(
        self,
        *,
        connection,
        session_row,
        message_row,
        last_visible_row,
    ) -> str:
        snapshot = self.snapshot_service.create_snapshot(
            session_id=session_row["id"],
            snapshot_type="edit_cutoff",
            message_id=message_row["id"],
            message_sequence=last_visible_row["sequence"],
            inclusive=True,
            state_snapshot_id=self._capture_state_snapshot_id(session_row),
            label=f"Edit cutoff before message {message_row['sequence']}",
            summary={
                "edit_target_message_id": message_row["id"],
                "restore_visible_through_sequence": last_visible_row["sequence"],
                "message_before_edit": {
                    "content": message_row["content"],
                    "raw_content": message_row["raw_content"],
                    "structured_content": json.loads(message_row["structured_content"]),
                    "is_edited": bool(message_row["is_edited"]),
                }
            },
            connection=connection,
        )
        return snapshot.id

    def _create_rollback_snapshot(
        self,
        *,
        connection,
        session_row,
        message_row,
        last_visible_row,
    ) -> str:
        snapshot = self.snapshot_service.create_snapshot(
            session_id=session_row["id"],
            snapshot_type="rollback_point",
            message_id=message_row["id"],
            message_sequence=last_visible_row["sequence"],
            inclusive=True,
            state_snapshot_id=self._capture_state_snapshot_id(session_row),
            label=f"Rollback point before hiding from message {message_row['sequence']}",
            summary={
                "target_message_id": message_row["id"],
                "restore_visible_through_sequence": last_visible_row["sequence"],
                "target_role": message_row["role"],
            },
            connection=connection,
        )
        return snapshot.id

    def _apply_assistant_generation(
        self,
        *,
        connection,
        session_row,
        user_message_row,
        assistant_message_id: str,
        swipe_id: str,
        trace_id: str,
        assistant_text: str,
        target_model: str,
        provider_name: str,
        finish_reason: str,
        usage: dict,
        raw_provider_response: dict,
        prompt_build,
        now: str,
        create_message_row: bool,
    ) -> None:
        messages = MessageRepository(connection)
        traces = PromptTraceRepository(connection)

        if create_message_row:
            assistant_message_values = {
                "id": assistant_message_id,
                "session_id": session_row["id"],
                "role": "assistant",
                "sequence": user_message_row["sequence"] + 1,
                "reply_to_message_id": user_message_row["id"],
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

        cleaned_assistant_text = assistant_text
        display_assistant_text = assistant_text
        self.state_service.restore_state_before_sequence(
            session_id=session_row["id"],
            sequence=user_message_row["sequence"] + 1,
            connection=connection,
        )
        state_parse_result = self.state_service.parse_and_apply_model_update(
            session_row=SessionRepository(connection).get_session(session_row["id"]),
            message_id=assistant_message_id,
            assistant_text=assistant_text,
            connection=connection,
        )
        if state_parse_result.raw_block:
            cleaned_assistant_text = self.state_service.strip_state_update_block(
                assistant_text
            )
            display_assistant_text = cleaned_assistant_text

        messages.update_message_content(
            assistant_message_id,
            content=display_assistant_text,
            raw_content=assistant_text,
            updated_at=now,
        )

        trace_token_stats = {
            **prompt_build.build_token_stats.model_dump(),
            **usage,
            "history_message_count": prompt_build.history_summary.message_count,
            "history_role_counts": prompt_build.history_summary.role_counts,
            "requested_model": target_model,
            "response_finish_reason": finish_reason,
        }
        trace_raw_response = {
            "request": {
                "model_name": target_model,
                "mode": session_row["mode"],
                "provider_name": provider_name,
                "message_count": len(prompt_build.final_messages),
                "history_summary": prompt_build.history_summary.model_dump(),
                "build_token_stats": prompt_build.build_token_stats.model_dump(),
            },
            "response": raw_provider_response,
        }
        trace_values = {
            "id": trace_id,
            "session_id": session_row["id"],
            "message_id": user_message_row["id"],
            "swipe_id": None,
            "mode": session_row["mode"],
            "raw_user_input": prompt_build.raw_user_input,
            "normalized_input": prompt_build.normalized_input,
            "preset_layers": json.dumps(prompt_build.preset_layers, ensure_ascii=False),
            "injection_items": json.dumps(
                [item.model_dump() for item in prompt_build.injection_items],
                ensure_ascii=False,
            ),
            "final_messages": json.dumps(prompt_build.final_messages, ensure_ascii=False),
            "token_stats": json.dumps(trace_token_stats, ensure_ascii=False),
            "tool_calls": "[]",
            "raw_response": json.dumps(trace_raw_response, ensure_ascii=False),
            "cleaned_response": cleaned_assistant_text,
            "display_response": display_assistant_text,
            "regex_hits": "[]",
            "state_update": json.dumps(state_parse_result.model_dump(), ensure_ascii=False),
            "created_at": now,
        }
        traces.create_prompt_trace(trace_values)

        swipe_values = {
            "id": swipe_id,
            "message_id": assistant_message_id,
            "swipe_index": messages.get_next_swipe_index(assistant_message_id),
            "generation_status": "completed",
            "raw_response": assistant_text,
            "cleaned_response": cleaned_assistant_text,
            "display_response": display_assistant_text,
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

    def list_messages(self, session_id: str) -> list[MessageResponse]:
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            session_row = sessions.get_session(session_id)
            if session_row is None:
                raise NotFoundError(f"Session not found: {session_id}")

            self.state_service.initialize_session_state(session_id)
            session_row = sessions.get_session(session_id)

            messages = MessageRepository(connection)
            media = MediaRepository(connection)
            rows = messages.list_messages_by_session(session_id)
            message_ids = [row["id"] for row in rows]
            swipe_rows = messages.list_swipes_by_message_ids(message_ids)
            attachment_rows = media.list_attachments_by_message_ids(message_ids)

            swipes_by_message: dict[str, list[MessageSwipeResponse]] = {}
            for swipe_row in swipe_rows:
                swipe = _swipe_row_to_response(swipe_row)
                swipes_by_message.setdefault(swipe.message_id, []).append(swipe)

            attachments_by_message: dict[str, list[MessageAttachmentResponse]] = {}
            for attachment_row in attachment_rows:
                attachment = _attachment_row_to_response(attachment_row)
                attachments_by_message.setdefault(attachment.message_id, []).append(attachment)

            responses = []
            for row in rows:
                response = _message_row_to_response(
                    row, swipes_by_message.get(row["id"], [])
                )
                response.attachments = attachments_by_message.get(row["id"], [])
                responses.append(response)
            return responses

    def get_message(self, message_id: str) -> MessageResponse:
        with get_connection() as connection:
            return self._get_message_with_swipes(connection=connection, message_id=message_id)

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
            media = MediaRepository(connection)

            session_row = sessions.get_session(session_id)
            if session_row is None:
                raise NotFoundError(f"Session not found: {session_id}")

            self.state_service.initialize_session_state(session_id)
            session_row = sessions.get_session(session_id)

            last_sequence = messages.get_last_sequence(session_id)
            history_rows = messages.list_messages_by_session(session_id)
            user_sequence = last_sequence + 1
            structured_content = self._build_reference_structured_content(
                structured_content=payload.structured_content,
                references=payload.references,
            )
            reference_items = self._resolve_reference_items(
                connection=connection,
                session_row=session_row,
                references=payload.references,
            )

            user_message_values = {
                "id": user_message_id,
                "session_id": session_id,
                "role": "user",
                "sequence": user_sequence,
                "reply_to_message_id": None,
                "content": payload.content,
                "raw_content": payload.content,
                "structured_content": json.dumps(structured_content, ensure_ascii=False),
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
            self._bind_message_attachments(
                connection=connection,
                message_id=user_message_id,
                attachments=payload.attachments,
                now=now,
            )
            self._maybe_auto_rename_chat_session(
                connection=connection,
                session_row=session_row,
                history_rows=history_rows,
                first_user_message=payload.content,
                now=now,
            )
            user_attachment_rows = media.list_attachments_by_message_ids([user_message_id])

            prompt_build = self.prompt_pipeline.build(
                session_row=session_row,
                history_rows=history_rows,
                current_user_input=payload.content,
                current_attachment_rows=user_attachment_rows,
                cards=cards,
                worldbooks=worldbooks,
                extra_injection_items=reference_items,
            )
            final_messages = prompt_build.final_messages

            (
                target_model,
                provider_name,
                finish_reason,
                usage,
                raw_provider_response,
                assistant_text,
            ) = self._generate_model_reply(
                session_row=session_row,
                final_messages=final_messages,
                fallback_user_content=prompt_build.normalized_input,
            )

            user_row = messages.get_message(user_message_id)
            self._apply_assistant_generation(
                connection=connection,
                session_row=session_row,
                user_message_row=user_row,
                assistant_message_id=assistant_message_id,
                swipe_id=swipe_id,
                trace_id=trace_id,
                assistant_text=assistant_text,
                target_model=target_model,
                provider_name=provider_name,
                finish_reason=finish_reason,
                usage=usage,
                raw_provider_response=raw_provider_response,
                prompt_build=prompt_build,
                now=now,
                create_message_row=True,
            )

            sessions.update_session_activity(
                session_id=session_id,
                message_count=session_row["message_count"] + 2,
                last_message_id=assistant_message_id,
                last_message_at=now,
                updated_at=now,
            )
            self.memory_summary_service.maybe_generate_next_summary(
                session_id=session_id,
                connection=connection,
            )
            self.long_term_memory_service.maybe_auto_extract_for_session(
                session_id=session_id,
                connection=connection,
            )

            assistant_row = messages.get_message(assistant_message_id)
            assistant_swipe_rows = messages.list_swipes_by_message_ids([assistant_message_id])

        assistant_swipes = [_swipe_row_to_response(row) for row in assistant_swipe_rows]
        return SendMessageResponse(
            user_message=self.get_message(user_message_id),
            assistant_message=_message_row_to_response(assistant_row, assistant_swipes),
        )

    def update_message(self, message_id: str, payload: UpdateMessageRequest) -> UpdateMessageResponse:
        now = utc_now_iso()
        with get_connection() as connection:
            messages = MessageRepository(connection)
            sessions = SessionRepository(connection)

            message_row = messages.get_message(message_id)
            if message_row is None or bool(message_row["is_hidden"]):
                raise NotFoundError(f"Message not found: {message_id}")
            if message_row["role"] != "user":
                raise AppError("Only user messages can be edited.", status_code=400)
            if bool(message_row["is_locked"]):
                raise AppError("Locked message cannot be edited.", status_code=400)

            session_row = sessions.get_session(message_row["session_id"])
            if session_row is None:
                raise NotFoundError(f"Session not found: {message_row['session_id']}")

            previous_visible = messages.list_messages_by_session(message_row["session_id"])
            last_visible_row = previous_visible[-1] if previous_visible else message_row
            self._create_edit_cutoff_snapshot(
                connection=connection,
                session_row=session_row,
                message_row=message_row,
                last_visible_row=last_visible_row,
            )
            messages.hide_messages_from_sequence(
                message_row["session_id"], message_row["sequence"] + 1, now
            )
            self.long_term_memory_service.cleanup_auto_memories_from_sequence(
                session_id=message_row["session_id"],
                sequence=message_row["sequence"] + 1,
                connection=connection,
            )
            messages.update_message_content(
                message_id,
                content=payload.content,
                raw_content=payload.content,
                structured_content=json.dumps(payload.structured_content, ensure_ascii=False),
                is_edited=1,
                updated_at=now,
            )
            self._replace_message_attachments(
                connection=connection,
                message_id=message_id,
                attachments=payload.attachments,
                now=now,
            )
            self.state_service.restore_state_before_sequence(
                session_id=message_row["session_id"],
                sequence=message_row["sequence"] + 1,
                connection=connection,
            )

            visible_rows = messages.list_messages_by_session(message_row["session_id"])
            last_visible = visible_rows[-1] if visible_rows else None
            sessions.update_session_activity(
                session_id=message_row["session_id"],
                message_count=len(visible_rows),
                last_message_id=last_visible["id"] if last_visible else None,
                last_message_at=last_visible["created_at"] if last_visible else None,
                updated_at=now,
            )

            truncated_count = max(0, len(previous_visible) - len(visible_rows))
            return UpdateMessageResponse(
                message=self._get_message_with_swipes(connection=connection, message_id=message_id),
                truncated_count=truncated_count,
            )

    def regenerate_message(
        self, message_id: str, payload: RegenerateMessageRequest
    ) -> MessageResponse:
        now = utc_now_iso()
        trace_id = new_id()
        swipe_id = new_id()
        with get_connection() as connection:
            messages = MessageRepository(connection)
            sessions = SessionRepository(connection)

            assistant_row = messages.get_message(message_id)
            if assistant_row is None or bool(assistant_row["is_hidden"]):
                raise NotFoundError(f"Message not found: {message_id}")
            if assistant_row["role"] != "assistant":
                raise AppError("Only assistant messages can be regenerated.", status_code=400)

            last_visible = messages.get_last_visible_message(assistant_row["session_id"])
            if last_visible is None or last_visible["id"] != assistant_row["id"]:
                raise AppError("Only the latest assistant message can be regenerated.", status_code=400)

            user_row = messages.get_message(assistant_row["reply_to_message_id"])
            if user_row is None:
                raise AppError("Regenerate target is missing its user message.", status_code=400)

            session_row = sessions.get_session(assistant_row["session_id"])
            prompt_build = self._build_prompt_for_user_message(
                session_row=session_row,
                user_message_row=user_row,
                connection=connection,
            )
            (
                target_model,
                provider_name,
                finish_reason,
                usage,
                raw_provider_response,
                assistant_text,
            ) = self._generate_model_reply(
                session_row=session_row,
                final_messages=prompt_build.final_messages,
                fallback_user_content=prompt_build.normalized_input,
                model_name_override=payload.model_name,
            )
            self._apply_assistant_generation(
                connection=connection,
                session_row=session_row,
                user_message_row=user_row,
                assistant_message_id=assistant_row["id"],
                swipe_id=swipe_id,
                trace_id=trace_id,
                assistant_text=assistant_text,
                target_model=target_model,
                provider_name=provider_name,
                finish_reason=finish_reason,
                usage=usage,
                raw_provider_response=raw_provider_response,
                prompt_build=prompt_build,
                now=now,
                create_message_row=False,
            )
            sessions.update_session_activity(
                session_id=assistant_row["session_id"],
                message_count=session_row["message_count"],
                last_message_id=assistant_row["id"],
                last_message_at=assistant_row["created_at"],
                updated_at=now,
            )
            self.long_term_memory_service.refresh_auto_memory_for_message(
                session_id=assistant_row["session_id"],
                assistant_message_id=assistant_row["id"],
                connection=connection,
            )
            return self._get_message_with_swipes(connection=connection, message_id=assistant_row["id"])

    def activate_swipe(self, message_id: str, swipe_id: str) -> MessageResponse:
        now = utc_now_iso()
        with get_connection() as connection:
            messages = MessageRepository(connection)
            sessions = SessionRepository(connection)

            assistant_row = messages.get_message(message_id)
            if assistant_row is None or bool(assistant_row["is_hidden"]):
                raise NotFoundError(f"Message not found: {message_id}")
            if assistant_row["role"] != "assistant":
                raise AppError("Only assistant messages support swipes.", status_code=400)

            last_visible = messages.get_last_visible_message(assistant_row["session_id"])
            if last_visible is None or last_visible["id"] != assistant_row["id"]:
                raise AppError("Only the latest assistant message can switch swipe.", status_code=400)

            swipe_row = messages.get_swipe(swipe_id)
            if swipe_row is None or swipe_row["message_id"] != assistant_row["id"]:
                raise NotFoundError(f"Swipe not found: {swipe_id}")

            self.state_service.restore_state_before_sequence(
                session_id=assistant_row["session_id"],
                sequence=assistant_row["sequence"],
                connection=connection,
            )
            session_row = sessions.get_session(assistant_row["session_id"])
            self.state_service.parse_and_apply_model_update(
                session_row=session_row,
                message_id=assistant_row["id"],
                assistant_text=swipe_row["raw_response"] or "",
                connection=connection,
            )
            messages.update_message_content(
                assistant_row["id"],
                content=swipe_row["display_response"] or swipe_row["raw_response"] or "",
                raw_content=swipe_row["raw_response"] or "",
                updated_at=now,
            )
            messages.update_message_active_swipe(assistant_row["id"], swipe_id, now)
            sessions.update_session_activity(
                session_id=assistant_row["session_id"],
                message_count=session_row["message_count"],
                last_message_id=assistant_row["id"],
                last_message_at=assistant_row["created_at"],
                updated_at=now,
            )
            self.long_term_memory_service.refresh_auto_memory_for_message(
                session_id=assistant_row["session_id"],
                assistant_message_id=assistant_row["id"],
                connection=connection,
            )
            return self._get_message_with_swipes(connection=connection, message_id=assistant_row["id"])

    def rollback_from_message(self, session_id: str, message_id: str) -> RollbackResponse:
        now = utc_now_iso()
        with get_connection() as connection:
            messages = MessageRepository(connection)
            sessions = SessionRepository(connection)

            session_row = sessions.get_session(session_id)
            if session_row is None:
                raise NotFoundError(f"Session not found: {session_id}")

            message_row = messages.get_message(message_id)
            if message_row is None or message_row["session_id"] != session_id:
                raise NotFoundError(f"Message not found in session: {message_id}")
            if bool(message_row["is_hidden"]):
                raise AppError("Message is already hidden.", status_code=400)
            if bool(message_row["is_locked"]):
                raise AppError("Locked message cannot be rolled back.", status_code=400)

            last_visible_row = messages.get_last_visible_message(session_id)
            snapshot_id = self._create_rollback_snapshot(
                connection=connection,
                session_row=session_row,
                message_row=message_row,
                last_visible_row=last_visible_row or message_row,
            )
            messages.hide_messages_from_sequence(session_id, message_row["sequence"], now)
            self.long_term_memory_service.cleanup_auto_memories_from_sequence(
                session_id=session_id,
                sequence=message_row["sequence"],
                connection=connection,
            )
            self.state_service.restore_state_before_sequence(
                session_id=session_id,
                sequence=message_row["sequence"],
                connection=connection,
            )
            visible_rows = messages.list_messages_by_session(session_id)
            last_visible = visible_rows[-1] if visible_rows else None
            sessions.update_session_activity(
                session_id=session_id,
                message_count=len(visible_rows),
                last_message_id=last_visible["id"] if last_visible else None,
                last_message_at=last_visible["created_at"] if last_visible else None,
                updated_at=now,
            )
            return RollbackResponse(
                session_id=session_id,
                message_count=len(visible_rows),
                last_message_id=last_visible["id"] if last_visible else None,
                rollback_to_message_id=last_visible["id"] if last_visible else None,
                snapshot_id=snapshot_id,
            )

    def toggle_message_lock(
        self, message_id: str, payload: ToggleMessageLockRequest
    ) -> MessageResponse:
        now = utc_now_iso()
        with get_connection() as connection:
            messages = MessageRepository(connection)
            message_row = messages.get_message(message_id)
            if message_row is None or bool(message_row["is_hidden"]):
                raise NotFoundError(f"Message not found: {message_id}")
            messages.update_message_lock(
                message_id,
                is_locked=payload.is_locked,
                updated_at=now,
            )
            return self._get_message_with_swipes(
                connection=connection, message_id=message_id
            )

    def delete_swipe(self, message_id: str, swipe_id: str) -> DeleteSwipeResponse:
        now = utc_now_iso()
        with get_connection() as connection:
            messages = MessageRepository(connection)
            assistant_row = messages.get_message(message_id)
            if assistant_row is None or bool(assistant_row["is_hidden"]):
                raise NotFoundError(f"Message not found: {message_id}")
            if assistant_row["role"] != "assistant":
                raise AppError("Only assistant messages have swipes.", 400)

            swipe_row = messages.get_swipe(swipe_id)
            if swipe_row is None or swipe_row["message_id"] != message_id:
                raise NotFoundError(f"Swipe not found: {swipe_id}")

            swipe_rows = messages.list_swipes_by_message_ids([message_id])
            if len(swipe_rows) <= 1:
                raise AppError("At least one swipe must be kept.", 400)

            next_active_swipe_id = assistant_row["active_swipe_id"]
            if swipe_id == assistant_row["active_swipe_id"]:
                next_active_swipe_id = next(
                    (
                        row["id"]
                        for row in swipe_rows
                        if row["id"] != swipe_id
                    ),
                    None,
                )
                if next_active_swipe_id is None:
                    raise AppError("Unable to select fallback swipe.", 400)
                next_active_swipe = messages.get_swipe(next_active_swipe_id)
                messages.update_message_content(
                    message_id,
                    content=next_active_swipe["display_response"]
                    or next_active_swipe["raw_response"]
                    or "",
                    raw_content=next_active_swipe["raw_response"] or "",
                    updated_at=now,
                )
                messages.update_message_active_swipe(
                    message_id, next_active_swipe_id, now
                )

            messages.delete_swipe(swipe_id)
            return DeleteSwipeResponse(
                message_id=message_id,
                deleted_swipe_id=swipe_id,
                active_swipe_id=next_active_swipe_id,
            )
