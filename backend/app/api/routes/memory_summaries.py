from fastapi import APIRouter

from app.schemas.memory_summaries import (
    MemorySummaryGenerateResponse,
    MemorySummaryResponse,
)
from app.services.memory_summaries import MemorySummaryService

router = APIRouter(tags=["memory_summaries"])

service = MemorySummaryService()


@router.get(
    "/sessions/{session_id}/memory-summaries",
    response_model=list[MemorySummaryResponse],
)
async def list_memory_summaries(session_id: str) -> list[MemorySummaryResponse]:
    return service.list_session_summaries(session_id)


@router.post(
    "/sessions/{session_id}/memory-summaries/generate",
    response_model=MemorySummaryGenerateResponse,
)
async def generate_memory_summary(session_id: str) -> MemorySummaryGenerateResponse:
    return service.maybe_generate_next_summary(session_id=session_id)
