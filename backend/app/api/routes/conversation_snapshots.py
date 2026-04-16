from fastapi import APIRouter

from app.schemas.conversation_snapshots import (
    ConversationSnapshotResponse,
    RestoreConversationSnapshotResponse,
)
from app.services.conversation_snapshots import ConversationSnapshotService

router = APIRouter(tags=["conversation_snapshots"])

service = ConversationSnapshotService()


@router.get(
    "/sessions/{session_id}/snapshots",
    response_model=list[ConversationSnapshotResponse],
)
async def list_snapshots(session_id: str) -> list[ConversationSnapshotResponse]:
    return service.list_snapshots(session_id)


@router.post(
    "/sessions/{session_id}/snapshots/{snapshot_id}/restore",
    response_model=RestoreConversationSnapshotResponse,
)
async def restore_snapshot(
    session_id: str,
    snapshot_id: str,
) -> RestoreConversationSnapshotResponse:
    return service.restore_snapshot(session_id=session_id, snapshot_id=snapshot_id)
