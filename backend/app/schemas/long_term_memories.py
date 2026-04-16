from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class LongTermMemoryResponse(BaseModel):
    id: str
    scope_type: str
    scope_id: str
    content: str
    type: str
    importance: str
    source_message_id: str | None = None
    created_at: datetime


class CreateLongTermMemoryRequest(BaseModel):
    scope_type: Literal["session", "card", "global"]
    scope_id: str
    content: str
    importance: Literal["high", "medium", "low"] = "medium"
    source_message_id: str | None = None

    @model_validator(mode="after")
    def validate_payload(self):
        if not self.content.strip():
            raise ValueError("Memory content must not be empty.")
        return self


class UpdateLongTermMemoryRequest(BaseModel):
    content: str
    importance: Literal["high", "medium", "low"] = "medium"

    @model_validator(mode="after")
    def validate_payload(self):
        if not self.content.strip():
            raise ValueError("Memory content must not be empty.")
        return self


class MarkMessageAsLongTermMemoryRequest(BaseModel):
    content: str | None = None
    scope_type: Literal["session", "card", "global"] | None = None
    importance: Literal["high", "medium", "low"] = "medium"


class DeleteLongTermMemoryResponse(BaseModel):
    deleted: bool = True
    memory_id: str


class ScopeMemoryListResponse(BaseModel):
    items: list[LongTermMemoryResponse] = Field(default_factory=list)


class AutoExtractLongTermMemoryResponse(BaseModel):
    created: bool
    memory: LongTermMemoryResponse | None = None
