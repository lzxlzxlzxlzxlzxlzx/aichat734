from datetime import datetime, timezone
import json

from app.core.database import get_connection
from app.core.exceptions import NotFoundError, ValidationError
from app.core.ids import new_id
from app.repositories.cards import CardRepository
from app.repositories.media import MediaRepository
from app.repositories.messages import MessageRepository
from app.repositories.sessions import SessionRepository
from app.repositories.states import StateRepository
from app.schemas.sessions import (
    SessionCopyRequest,
    SessionCopyResponse,
    SessionCreateRequest,
    SessionResponse,
)
from app.services.conversation_snapshots import ConversationSnapshotService
from app.services.states import StateService


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_session_response(row) -> SessionResponse:
    return SessionResponse(
        id=row["id"],
        mode=row["mode"],
        name=row["name"],
        status=row["status"],
        card_id=row["card_id"],
        card_version_id=row["card_version_id"],
        worldbook_id=row["worldbook_id"],
        project_id=row["project_id"],
        persona_id=row["persona_id"],
        preset_version_id=row["preset_version_id"],
        origin_session_id=row["origin_session_id"],
        origin_snapshot_id=row["origin_snapshot_id"],
        message_count=row["message_count"],
        last_message_id=row["last_message_id"],
        last_message_at=row["last_message_at"],
        current_state_snapshot_id=row["current_state_snapshot_id"],
        model_name=row["model_name"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class SessionService:
    def __init__(self) -> None:
        self.state_service = StateService()
        self.snapshot_service = ConversationSnapshotService()

    def _resolve_session_defaults(
        self,
        *,
        payload: SessionCreateRequest,
        cards: CardRepository,
    ) -> tuple[str | None, str | None, str | None]:
        card_id = payload.card_id
        card_version_id = payload.card_version_id
        worldbook_id = payload.worldbook_id

        if payload.mode == "play":
            if not card_id:
                raise ValidationError("Play session requires card_id.")
            card = cards.get_card(card_id)
            if card is None:
                raise NotFoundError(f"Character card not found: {card_id}")
            if not card_version_id:
                card_version_id = (
                    card["current_published_version_id"]
                    or card["current_draft_version_id"]
                )
            if not worldbook_id:
                worldbook_id = card["worldbook_id"]

        if payload.mode == "creation" and not payload.project_id:
            raise ValidationError("Creation session requires project_id.")

        return card_id, card_version_id, worldbook_id

    def _create_session_record(
        self,
        *,
        sessions: SessionRepository,
        cards: CardRepository,
        payload: SessionCreateRequest,
        now: str,
        session_id: str | None = None,
    ):
        session_id = session_id or new_id()
        card_id, card_version_id, worldbook_id = self._resolve_session_defaults(
            payload=payload,
            cards=cards,
        )

        values = {
            "id": session_id,
            "mode": payload.mode,
            "name": payload.name,
            "status": payload.status,
            "card_id": card_id,
            "card_version_id": card_version_id,
            "worldbook_id": worldbook_id,
            "project_id": payload.project_id,
            "persona_id": payload.persona_id,
            "preset_version_id": payload.preset_version_id,
            "origin_session_id": payload.origin_session_id,
            "origin_snapshot_id": payload.origin_snapshot_id,
            "message_count": 0,
            "last_message_id": None,
            "last_message_at": None,
            "current_state_snapshot_id": None,
            "model_name": payload.model_name,
            "created_at": now,
            "updated_at": now,
        }
        sessions.create_session(values)

        if card_id:
            sessions.update_latest_session_for_card(card_id, session_id, now)

        return sessions.get_session(session_id)

    def list_sessions(self) -> list[SessionResponse]:
        with get_connection() as connection:
            repository = SessionRepository(connection)
            rows = repository.list_sessions()
            return [_row_to_session_response(row) for row in rows]

    def get_session(self, session_id: str) -> SessionResponse:
        with get_connection() as connection:
            repository = SessionRepository(connection)
            row = repository.get_session(session_id)
            if row is None:
                raise NotFoundError(f"Session not found: {session_id}")
            return _row_to_session_response(row)

    def create_session(self, payload: SessionCreateRequest) -> SessionResponse:
        now = _utc_now()

        with get_connection() as connection:
            sessions = SessionRepository(connection)
            cards = CardRepository(connection)
            session_row = self._create_session_record(
                sessions=sessions,
                cards=cards,
                payload=payload,
                now=now,
            )

        response = _row_to_session_response(session_row)
        self.state_service.initialize_session_state(response.id)
        return response

    def copy_session(
        self, source_session_id: str, payload: SessionCopyRequest
    ) -> SessionCopyResponse:
        now = _utc_now()
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            cards = CardRepository(connection)
            messages = MessageRepository(connection)
            media = MediaRepository(connection)
            states = StateRepository(connection)

            source_session = sessions.get_session(source_session_id)
            if source_session is None:
                raise NotFoundError(f"Session not found: {source_session_id}")

            source_message = None
            if payload.source_message_id:
                source_message = messages.get_message(payload.source_message_id)
                if (
                    source_message is None
                    or source_message["session_id"] != source_session_id
                    or bool(source_message["is_hidden"])
                ):
                    raise NotFoundError(
                        f"Message not found in session: {payload.source_message_id}"
                    )
                cutoff_sequence = source_message["sequence"]
            else:
                source_message = messages.get_last_visible_message(source_session_id)
                cutoff_sequence = source_message["sequence"] if source_message else 0

            if cutoff_sequence > 0:
                visible_rows = messages.list_messages_through_sequence(
                    source_session_id, cutoff_sequence
                )
            else:
                visible_rows = []

            state_snapshot_row = None
            if cutoff_sequence > 0:
                state_snapshot_row = states.get_latest_state_snapshot_before_sequence(
                    source_session_id, cutoff_sequence + 1
                )
            elif source_session["current_state_snapshot_id"]:
                state_snapshot_row = states.get_state_snapshot(
                    source_session["current_state_snapshot_id"]
                )
            if state_snapshot_row is None:
                initialized = self.state_service.initialize_session_state(source_session_id)
                state_snapshot_row = states.get_state_snapshot(initialized.snapshot_id)

            source_snapshot = self.snapshot_service.create_snapshot(
                session_id=source_session_id,
                snapshot_type="copy_source",
                message_id=source_message["id"] if source_message else None,
                message_sequence=cutoff_sequence,
                inclusive=True,
                state_snapshot_id=state_snapshot_row["id"] if state_snapshot_row else None,
                label=f"Copy source at sequence {cutoff_sequence}",
                summary={
                    "copied_message_count": len(visible_rows),
                    "copied_through_sequence": cutoff_sequence,
                    "source_message_id": source_message["id"] if source_message else None,
                },
                connection=connection,
            )

            create_payload = SessionCreateRequest(
                mode=source_session["mode"],
                name=payload.name,
                status="active",
                card_id=source_session["card_id"],
                card_version_id=source_session["card_version_id"],
                worldbook_id=source_session["worldbook_id"],
                project_id=source_session["project_id"],
                persona_id=source_session["persona_id"],
                preset_version_id=source_session["preset_version_id"],
                origin_session_id=source_session_id,
                origin_snapshot_id=source_snapshot.id,
                model_name=source_session["model_name"],
            )
            new_session_row = self._create_session_record(
                sessions=sessions,
                cards=cards,
                payload=create_payload,
                now=now,
            )
            new_session_id = new_session_row["id"]

            message_id_map: dict[str, str] = {}
            active_swipes = {
                row["id"]: row
                for row in messages.list_swipes_by_message_ids(
                    [
                        row["id"]
                        for row in visible_rows
                        if row["role"] == "assistant"
                    ]
                )
            }
            attachments_by_message: dict[str, list] = {}
            for attachment_row in media.list_attachments_by_message_ids(
                [row["id"] for row in visible_rows]
            ):
                attachments_by_message.setdefault(
                    attachment_row["message_id"], []
                ).append(attachment_row)

            for row in visible_rows:
                new_message_id = new_id()
                message_id_map[row["id"]] = new_message_id
                new_active_swipe_id = new_id() if row["role"] == "assistant" else None
                messages.create_message(
                    {
                        "id": new_message_id,
                        "session_id": new_session_id,
                        "role": row["role"],
                        "sequence": row["sequence"],
                        "reply_to_message_id": (
                            message_id_map.get(row["reply_to_message_id"])
                            if row["reply_to_message_id"]
                            else None
                        ),
                        "content": row["content"],
                        "raw_content": row["raw_content"],
                        "structured_content": row["structured_content"],
                        "active_swipe_id": new_active_swipe_id,
                        "token_count": row["token_count"],
                        "is_hidden": 0,
                        "is_locked": row["is_locked"],
                        "is_edited": row["is_edited"],
                        "source_type": row["source_type"],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                    }
                )

                if row["role"] == "assistant":
                    source_swipe = active_swipes.get(row["active_swipe_id"] or "")
                    messages.create_message_swipe(
                        {
                            "id": new_active_swipe_id,
                            "message_id": new_message_id,
                            "swipe_index": 0,
                            "generation_status": (
                                source_swipe["generation_status"]
                                if source_swipe is not None
                                else "completed"
                            ),
                            "raw_response": (
                                source_swipe["raw_response"]
                                if source_swipe is not None
                                else row["raw_content"]
                            ),
                            "cleaned_response": (
                                source_swipe["cleaned_response"]
                                if source_swipe is not None
                                else row["content"]
                            ),
                            "display_response": (
                                source_swipe["display_response"]
                                if source_swipe is not None
                                else row["content"]
                            ),
                            "provider_name": (
                                source_swipe["provider_name"]
                                if source_swipe is not None
                                else None
                            ),
                            "model_name": (
                                source_swipe["model_name"]
                                if source_swipe is not None
                                else source_session["model_name"]
                            ),
                            "finish_reason": (
                                source_swipe["finish_reason"]
                                if source_swipe is not None
                                else "copied"
                            ),
                            "token_usage": (
                                source_swipe["token_usage"]
                                if source_swipe is not None
                                else json.dumps({}, ensure_ascii=False)
                            ),
                            "trace_id": None,
                            "created_at": row["created_at"],
                        }
                    )

                for attachment_row in attachments_by_message.get(row["id"], []):
                    media.create_message_attachment(
                        {
                            "id": new_id(),
                            "message_id": new_message_id,
                            "media_asset_id": attachment_row["media_asset_id"],
                            "attachment_type": attachment_row["attachment_type"],
                            "order_index": attachment_row["order_index"],
                            "caption": attachment_row["caption"],
                            "created_at": attachment_row["attachment_created_at"],
                        }
                    )

            copied_state_snapshot_id = None
            if state_snapshot_row is not None:
                copied_state_snapshot_id = new_id()
                mapped_message_id = None
                if state_snapshot_row["message_id"]:
                    mapped_message_id = message_id_map.get(state_snapshot_row["message_id"])
                states.create_state_snapshot(
                    {
                        "id": copied_state_snapshot_id,
                        "session_id": new_session_id,
                        "message_id": mapped_message_id,
                        "variables": state_snapshot_row["variables"],
                        "created_at": now,
                    }
                )
                sessions.update_current_state_snapshot(
                    session_id=new_session_id,
                    snapshot_id=copied_state_snapshot_id,
                    updated_at=now,
                )

            last_message = visible_rows[-1] if visible_rows else None
            sessions.update_session_activity(
                session_id=new_session_id,
                message_count=len(visible_rows),
                last_message_id=(
                    message_id_map[last_message["id"]] if last_message is not None else None
                ),
                last_message_at=last_message["created_at"] if last_message is not None else None,
                updated_at=now,
            )

            final_session_row = sessions.get_session(new_session_id)

        return SessionCopyResponse(
            session=_row_to_session_response(final_session_row),
            source_snapshot_id=source_snapshot.id,
            copied_message_count=len(visible_rows),
        )
