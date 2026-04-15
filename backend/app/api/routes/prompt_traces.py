from fastapi import APIRouter

from app.schemas.prompt_traces import (
    PromptTraceInspectorResponse,
    PromptTraceSummaryResponse,
)
from app.services.prompt_traces import PromptTraceService

router = APIRouter(tags=["prompt-traces"])

service = PromptTraceService()


@router.get(
    "/sessions/{session_id}/traces",
    response_model=list[PromptTraceSummaryResponse],
)
async def list_session_traces(session_id: str) -> list[PromptTraceSummaryResponse]:
    return service.list_session_traces(session_id)


@router.get(
    "/sessions/{session_id}/traces/latest",
    response_model=PromptTraceInspectorResponse,
)
async def get_latest_trace_by_session(session_id: str) -> PromptTraceInspectorResponse:
    return service.get_latest_trace_by_session(session_id)


@router.get(
    "/messages/{message_id}/trace",
    response_model=PromptTraceInspectorResponse,
)
async def get_latest_trace_by_message(message_id: str) -> PromptTraceInspectorResponse:
    return service.get_latest_trace_by_message(message_id)


@router.get(
    "/prompt-traces/{trace_id}",
    response_model=PromptTraceInspectorResponse,
)
async def get_trace(trace_id: str) -> PromptTraceInspectorResponse:
    return service.get_trace(trace_id)
