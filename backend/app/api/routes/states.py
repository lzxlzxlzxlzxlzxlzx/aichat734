from fastapi import APIRouter

from app.schemas.states import (
    SessionStateResponse,
    StateChangeLogResponse,
    StateSnapshotResponse,
)
from app.services.states import StateService

router = APIRouter(tags=["states"])

service = StateService()


@router.get(
    "/sessions/{session_id}/state",
    response_model=SessionStateResponse,
)
async def get_current_state(session_id: str) -> SessionStateResponse:
    return service.get_current_state(session_id)


@router.get(
    "/sessions/{session_id}/state/snapshots",
    response_model=list[StateSnapshotResponse],
)
async def list_state_snapshots(session_id: str) -> list[StateSnapshotResponse]:
    return service.list_state_snapshots(session_id)


@router.get(
    "/sessions/{session_id}/state/changes",
    response_model=list[StateChangeLogResponse],
)
async def list_state_change_logs(session_id: str) -> list[StateChangeLogResponse]:
    return service.list_state_change_logs(session_id)
