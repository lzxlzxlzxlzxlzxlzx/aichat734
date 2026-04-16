from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.prompt_traces import PromptTraceInspectorResponse, PromptTraceSummaryResponse
from app.schemas.sessions import SessionResponse


class ChatSessionCreateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    model_name: str | None = None


class ChatSessionRenameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class ChatSessionStatusRequest(BaseModel):
    status: str = Field(pattern="^(active|archived)$")


class ChatSessionModelRequest(BaseModel):
    model_name: str = Field(min_length=1, max_length=200)


class ChatSessionSummaryResponse(BaseModel):
    id: str
    name: str
    status: str
    message_count: int
    last_message_id: str | None = None
    last_message_at: datetime | None = None
    model_name: str | None = None
    created_at: datetime
    updated_at: datetime


class ChatAssistantProfileResponse(BaseModel):
    name: str
    title: str
    summary: str
    traits: list[str] = Field(default_factory=list)


class ChatQuickReplyItem(BaseModel):
    id: str
    label: str
    content: str
    mode: str = "fill"
    order: int = 0


class ChatQuickReplyGroup(BaseModel):
    id: str
    name: str
    scope_type: str
    items: list[ChatQuickReplyItem] = Field(default_factory=list)


class ChatRecentCardSummaryResponse(BaseModel):
    id: str
    name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    cover_asset_id: str | None = None
    avatar_asset_id: str | None = None
    latest_session_id: str | None = None
    last_interaction_at: datetime | None = None


class ChatSessionOverviewResponse(BaseModel):
    session: SessionResponse
    assistant_profile: ChatAssistantProfileResponse
    quick_replies: list[ChatQuickReplyGroup] = Field(default_factory=list)
    recent_cards: list[ChatRecentCardSummaryResponse] = Field(default_factory=list)
    latest_trace: PromptTraceSummaryResponse | None = None


class ChatTraceListResponse(BaseModel):
    items: list[PromptTraceSummaryResponse] = Field(default_factory=list)


__all__ = [
    "ChatAssistantProfileResponse",
    "ChatQuickReplyGroup",
    "ChatQuickReplyItem",
    "ChatRecentCardSummaryResponse",
    "ChatSessionCreateRequest",
    "ChatSessionModelRequest",
    "ChatSessionOverviewResponse",
    "ChatSessionRenameRequest",
    "ChatSessionStatusRequest",
    "ChatSessionSummaryResponse",
    "ChatTraceListResponse",
    "PromptTraceInspectorResponse",
]
