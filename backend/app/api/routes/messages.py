from fastapi import APIRouter

from app.schemas.messages import MessageResponse, SendMessageRequest, SendMessageResponse
from app.services.messages import MessageService

router = APIRouter(prefix="/sessions/{session_id}/messages", tags=["messages"])

service = MessageService()


@router.get("", response_model=list[MessageResponse])
async def list_messages(session_id: str) -> list[MessageResponse]:
    return service.list_messages(session_id)


@router.post("", response_model=SendMessageResponse, status_code=201)
async def send_message(
    session_id: str, payload: SendMessageRequest
) -> SendMessageResponse:
    return service.send_message(session_id, payload)
