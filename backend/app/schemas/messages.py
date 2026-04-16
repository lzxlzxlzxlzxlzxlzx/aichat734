from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.schemas.media import MessageAttachmentBindRequest, MessageAttachmentResponse


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
    attachments: list[MessageAttachmentResponse] = Field(default_factory=list)


class MessageReferenceRequest(BaseModel):
    reference_type: str = Field(pattern="^(card|worldbook|session|message)$")
    target_id: str = Field(min_length=1)
    label: str | None = Field(default=None, max_length=200)
    max_messages: int | None = Field(default=None, ge=1, le=20)


class SendMessageRequest(BaseModel):
    content: str = ""
    structured_content: list[dict[str, Any]] | list[Any] = Field(default_factory=list)
    attachments: list[MessageAttachmentBindRequest] = Field(default_factory=list)
    references: list[MessageReferenceRequest] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_non_empty(self):
        if not self.content.strip() and not self.attachments and not self.references:
            raise ValueError("Message content or attachments must be provided.")
        return self


class SendMessageResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse


class UpdateMessageResponse(BaseModel):
    message: MessageResponse
    truncated_count: int = 0


class UpdateMessageRequest(BaseModel):
    content: str = ""
    structured_content: list[dict[str, Any]] | list[Any] = Field(default_factory=list)
    attachments: list[MessageAttachmentBindRequest] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_non_empty(self):
        if not self.content.strip() and not self.attachments:
            raise ValueError("Message content or attachments must be provided.")
        return self


class RegenerateMessageRequest(BaseModel):
    model_name: str | None = None


class ToggleMessageLockRequest(BaseModel):
    is_locked: bool


class DeleteSwipeResponse(BaseModel):
    message_id: str
    deleted_swipe_id: str
    active_swipe_id: str | None = None


class RollbackResponse(BaseModel):
    session_id: str
    message_count: int
    last_message_id: str | None = None
    rollback_to_message_id: str | None = None
    snapshot_id: str | None = None
