from typing import Any

from pydantic import BaseModel, Field


class ModelChatRequest(BaseModel):
    model_name: str
    mode: str
    messages: list[dict[str, Any]] = Field(default_factory=list)
    temperature: float = 0.9
    max_tokens: int = 1200


class ModelChatResponse(BaseModel):
    provider_name: str
    model_name: str
    content: str
    raw_response: dict[str, Any]
    finish_reason: str | None = None
    usage: dict[str, Any] = Field(default_factory=dict)
