from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MessageSwipeResponse(BaseModel):
    id: str
    message_id: str
    swipe_index: int
    generation_status: str
    raw_response: str | None = None
    cleaned_response: str | None = None
    display_response: str | None = None
    provider_name: str | None = None
    model_name: str | None = None
    finish_reason: str | None = None
    token_usage: dict[str, Any]
    trace_id: str | None = None
    created_at: datetime


class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    sequence: int
    reply_to_message_id: str | None = None
    content: str
    raw_content: str | None = None
    structured_content: list[dict[str, Any]] | list[Any]
    active_swipe_id: str | None = None
    token_count: int | None = None
    is_hidden: bool
    is_locked: bool
    is_edited: bool
    source_type: str
    created_at: datetime
    updated_at: datetime | None = None
    swipes: list[MessageSwipeResponse] = Field(default_factory=list)


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1)
    structured_content: list[dict[str, Any]] | list[Any] = Field(default_factory=list)


class SendMessageResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse
