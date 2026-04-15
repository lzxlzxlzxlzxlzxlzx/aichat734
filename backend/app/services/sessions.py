from datetime import datetime, timezone

from app.core.database import get_connection
from app.core.exceptions import NotFoundError, ValidationError
from app.core.ids import new_id
from app.repositories.cards import CardRepository
from app.repositories.sessions import SessionRepository
from app.schemas.sessions import SessionCreateRequest, SessionResponse


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
        session_id = new_id()

        with get_connection() as connection:
            sessions = SessionRepository(connection)
            cards = CardRepository(connection)

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

            session_row = sessions.get_session(session_id)

        return _row_to_session_response(session_row)
