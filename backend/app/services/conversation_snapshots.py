import json

from app.core.database import get_connection
from app.core.exceptions import NotFoundError
from app.core.ids import new_id
from app.core.time import utc_now_iso
from app.repositories.conversation_snapshots import ConversationSnapshotRepository
from app.repositories.messages import MessageRepository
from app.repositories.sessions import SessionRepository
from app.schemas.conversation_snapshots import (
    ConversationSnapshotResponse,
    RestoreConversationSnapshotResponse,
)
from app.services.states import StateService


def _safe_json_loads(value: str | None):
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {"raw": value}


def _row_to_snapshot_response(row) -> ConversationSnapshotResponse:
    memory_summary_ids = []
    if row["memory_summary_ids"]:
        try:
            memory_summary_ids = json.loads(row["memory_summary_ids"])
        except json.JSONDecodeError:
            memory_summary_ids = []

    return ConversationSnapshotResponse(
        id=row["id"],
        session_id=row["session_id"],
        snapshot_type=row["snapshot_type"],
        message_id=row["message_id"],
        message_sequence=row["message_sequence"],
        inclusive=bool(row["inclusive"]),
        state_snapshot_id=row["state_snapshot_id"],
        memory_summary_ids=memory_summary_ids,
        label=row["label"],
        summary=_safe_json_loads(row["summary"]),
        created_by=row["created_by"],
        created_at=row["created_at"],
    )


class ConversationSnapshotService:
    def __init__(self) -> None:
        self.state_service = StateService()

    def create_snapshot(
        self,
        *,
        session_id: str,
        snapshot_type: str,
        message_id: str | None,
        message_sequence: int,
        inclusive: bool,
        state_snapshot_id: str | None,
        label: str | None = None,
        summary: dict | None = None,
        created_by: str = "system",
        memory_summary_ids: list[str] | None = None,
        connection,
    ) -> ConversationSnapshotResponse:
        sessions = SessionRepository(connection)
        session_row = sessions.get_session(session_id)
        if session_row is None:
            raise NotFoundError(f"Session not found: {session_id}")

        snapshot_id = new_id()
        now = utc_now_iso()
        values = {
            "id": snapshot_id,
            "session_id": session_id,
            "snapshot_type": snapshot_type,
            "message_id": message_id,
            "message_sequence": message_sequence,
            "inclusive": 1 if inclusive else 0,
            "state_snapshot_id": state_snapshot_id,
            "memory_summary_ids": json.dumps(memory_summary_ids or [], ensure_ascii=False),
            "label": label,
            "summary": json.dumps(summary, ensure_ascii=False) if summary is not None else None,
            "created_by": created_by,
            "created_at": now,
        }
        repository = ConversationSnapshotRepository(connection)
        repository.create_snapshot(values)
        snapshot_row = repository.get_snapshot(snapshot_id)
        return _row_to_snapshot_response(snapshot_row)

    def list_snapshots(self, session_id: str) -> list[ConversationSnapshotResponse]:
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            if sessions.get_session(session_id) is None:
                raise NotFoundError(f"Session not found: {session_id}")

            repository = ConversationSnapshotRepository(connection)
            return [_row_to_snapshot_response(row) for row in repository.list_snapshots(session_id)]

    def restore_snapshot(
        self,
        *,
        session_id: str,
        snapshot_id: str,
    ) -> RestoreConversationSnapshotResponse:
        now = utc_now_iso()
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            messages = MessageRepository(connection)
            repository = ConversationSnapshotRepository(connection)

            session_row = sessions.get_session(session_id)
            if session_row is None:
                raise NotFoundError(f"Session not found: {session_id}")

            snapshot_row = repository.get_snapshot(snapshot_id)
            if snapshot_row is None or snapshot_row["session_id"] != session_id:
                raise NotFoundError(f"Conversation snapshot not found: {snapshot_id}")

            cutoff_sequence = (
                snapshot_row["message_sequence"]
                if bool(snapshot_row["inclusive"])
                else snapshot_row["message_sequence"] - 1
            )

            messages.restore_messages_through_sequence(session_id, cutoff_sequence, now)
            messages.hide_messages_after_sequence(session_id, cutoff_sequence, now)

            summary = _safe_json_loads(snapshot_row["summary"])
            if (
                snapshot_row["snapshot_type"] == "edit_cutoff"
                and snapshot_row["message_id"]
                and isinstance(summary, dict)
                and summary.get("message_before_edit")
            ):
                previous_message = summary["message_before_edit"]
                messages.update_message_content(
                    snapshot_row["message_id"],
                    content=previous_message.get("content") or "",
                    raw_content=previous_message.get("raw_content") or previous_message.get("content") or "",
                    structured_content=json.dumps(
                        previous_message.get("structured_content") or [],
                        ensure_ascii=False,
                    ),
                    is_edited=1 if previous_message.get("is_edited") else 0,
                    updated_at=now,
                )

            state_snapshot_id = snapshot_row["state_snapshot_id"]
            if state_snapshot_id:
                self.state_service.restore_state_snapshot(
                    session_id=session_id,
                    snapshot_id=state_snapshot_id,
                    connection=connection,
                )
            else:
                self.state_service.restore_state_before_sequence(
                    session_id=session_id,
                    sequence=cutoff_sequence + 1,
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

            return RestoreConversationSnapshotResponse(
                session_id=session_id,
                snapshot_id=snapshot_id,
                restored_message_count=len(visible_rows),
                last_message_id=last_visible["id"] if last_visible else None,
                rollback_to_message_id=last_visible["id"] if last_visible else None,
                state_snapshot_id=state_snapshot_id,
            )
