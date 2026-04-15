from typing import Any

from pydantic import BaseModel, Field


class PromptInjectionItem(BaseModel):
    id: str
    source_type: str
    source_id: str | None = None
    label: str
    content: str
    stage: str
    priority: int = 100
    token_estimate: int = 0
    mode: str


class PromptBuildResult(BaseModel):
    raw_user_input: str
    normalized_input: str
    preset_layers: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    injection_items: list[PromptInjectionItem] = Field(default_factory=list)
    final_messages: list[dict[str, Any]] = Field(default_factory=list)
