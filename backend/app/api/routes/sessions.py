from fastapi import APIRouter

from app.schemas.sessions import (
    SessionCopyRequest,
    SessionCopyResponse,
    SessionCreateRequest,
    SessionResponse,
)
from app.services.sessions import SessionService

router = APIRouter(prefix="/sessions", tags=["sessions"])

service = SessionService()


@router.get("", response_model=list[SessionResponse])
async def list_sessions() -> list[SessionResponse]:
    return service.list_sessions()


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str) -> SessionResponse:
    return service.get_session(session_id)


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(payload: SessionCreateRequest) -> SessionResponse:
    return service.create_session(payload)


@router.post("/{session_id}/copy", response_model=SessionCopyResponse, status_code=201)
async def copy_session(
    session_id: str, payload: SessionCopyRequest
) -> SessionCopyResponse:
    return service.copy_session(session_id, payload)
