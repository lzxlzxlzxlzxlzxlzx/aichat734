from fastapi import APIRouter

from app.schemas.messages import (
    DeleteSwipeResponse,
    MessageResponse,
    RegenerateMessageRequest,
    RollbackResponse,
    SendMessageRequest,
    SendMessageResponse,
    ToggleMessageLockRequest,
    UpdateMessageResponse,
    UpdateMessageRequest,
)
from app.services.messages import MessageService

router = APIRouter(tags=["messages"])

service = MessageService()


@router.get("/sessions/{session_id}/messages", response_model=list[MessageResponse])
async def list_messages(session_id: str) -> list[MessageResponse]:
    return service.list_messages(session_id)


@router.post(
    "/sessions/{session_id}/messages",
    response_model=SendMessageResponse,
    status_code=201,
)
async def send_message(
    session_id: str, payload: SendMessageRequest
) -> SendMessageResponse:
    return service.send_message(session_id, payload)


@router.get("/messages/{message_id}", response_model=MessageResponse)
async def get_message(message_id: str) -> MessageResponse:
    return service.get_message(message_id)


@router.patch("/messages/{message_id}", response_model=UpdateMessageResponse)
async def update_message(
    message_id: str, payload: UpdateMessageRequest
) -> UpdateMessageResponse:
    return service.update_message(message_id, payload)


@router.post("/messages/{message_id}/regenerate", response_model=MessageResponse)
async def regenerate_message(
    message_id: str, payload: RegenerateMessageRequest
) -> MessageResponse:
    return service.regenerate_message(message_id, payload)


@router.post(
    "/messages/{message_id}/swipes/{swipe_id}/activate",
    response_model=MessageResponse,
)
async def activate_swipe(message_id: str, swipe_id: str) -> MessageResponse:
    return service.activate_swipe(message_id, swipe_id)


@router.patch("/messages/{message_id}/lock", response_model=MessageResponse)
async def toggle_message_lock(
    message_id: str, payload: ToggleMessageLockRequest
) -> MessageResponse:
    return service.toggle_message_lock(message_id, payload)


@router.delete(
    "/messages/{message_id}/swipes/{swipe_id}",
    response_model=DeleteSwipeResponse,
)
async def delete_swipe(message_id: str, swipe_id: str) -> DeleteSwipeResponse:
    return service.delete_swipe(message_id, swipe_id)


@router.delete(
    "/sessions/{session_id}/messages/{message_id}",
    response_model=RollbackResponse,
)
async def delete_message(session_id: str, message_id: str) -> RollbackResponse:
    return service.rollback_from_message(session_id, message_id)


@router.post(
    "/sessions/{session_id}/messages/{message_id}/rollback",
    response_model=RollbackResponse,
)
async def rollback_from_message(
    session_id: str, message_id: str
) -> RollbackResponse:
    return service.rollback_from_message(session_id, message_id)
