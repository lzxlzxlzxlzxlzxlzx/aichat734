from fastapi import APIRouter, Query

from app.schemas.long_term_memories import (
    AutoExtractLongTermMemoryResponse,
    CreateLongTermMemoryRequest,
    DeleteLongTermMemoryResponse,
    LongTermMemoryResponse,
    MarkMessageAsLongTermMemoryRequest,
    UpdateLongTermMemoryRequest,
)
from app.services.long_term_memories import LongTermMemoryService

router = APIRouter(tags=["long_term_memories"])

service = LongTermMemoryService()


@router.get(
    "/sessions/{session_id}/long-term-memories",
    response_model=list[LongTermMemoryResponse],
)
async def list_long_term_memories(
    session_id: str,
    scope_type: str = Query(...),
    scope_id: str = Query(...),
) -> list[LongTermMemoryResponse]:
    return service.list_scope_memories(
        session_id=session_id,
        scope_type=scope_type,
        scope_id=scope_id,
    )


@router.post(
    "/sessions/{session_id}/long-term-memories",
    response_model=LongTermMemoryResponse,
    status_code=201,
)
async def create_long_term_memory(
    session_id: str, payload: CreateLongTermMemoryRequest
) -> LongTermMemoryResponse:
    return service.create_memory(session_id=session_id, payload=payload)


@router.patch(
    "/sessions/{session_id}/long-term-memories/{memory_id}",
    response_model=LongTermMemoryResponse,
)
async def update_long_term_memory(
    session_id: str,
    memory_id: str,
    payload: UpdateLongTermMemoryRequest,
) -> LongTermMemoryResponse:
    return service.update_memory(
        session_id=session_id,
        memory_id=memory_id,
        payload=payload,
    )


@router.delete(
    "/sessions/{session_id}/long-term-memories/{memory_id}",
    response_model=DeleteLongTermMemoryResponse,
)
async def delete_long_term_memory(
    session_id: str, memory_id: str
) -> DeleteLongTermMemoryResponse:
    return service.delete_memory(session_id=session_id, memory_id=memory_id)


@router.post(
    "/messages/{message_id}/long-term-memory",
    response_model=LongTermMemoryResponse,
    status_code=201,
)
async def mark_message_as_long_term_memory(
    message_id: str, payload: MarkMessageAsLongTermMemoryRequest
) -> LongTermMemoryResponse:
    return service.mark_message_as_memory(message_id=message_id, payload=payload)


@router.post(
    "/sessions/{session_id}/long-term-memories/auto-extract",
    response_model=AutoExtractLongTermMemoryResponse,
)
async def auto_extract_long_term_memory(
    session_id: str,
) -> AutoExtractLongTermMemoryResponse:
    return service.maybe_auto_extract_for_session(session_id=session_id)
