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


class PromptHistorySummary(BaseModel):
    message_count: int = 0
    first_sequence: int | None = None
    last_sequence: int | None = None
    role_counts: dict[str, int] = Field(default_factory=dict)


class PromptBuildTokenStats(BaseModel):
    raw_input_estimate: int = 0
    normalized_input_estimate: int = 0
    injection_total_estimate: int = 0
    history_total_estimate: int = 0
    final_messages_estimate: int = 0
    final_messages_count: int = 0


class PromptBuildResult(BaseModel):
    raw_user_input: str
    normalized_input: str
    preset_layers: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    injection_items: list[PromptInjectionItem] = Field(default_factory=list)
    final_messages: list[dict[str, Any]] = Field(default_factory=list)
    history_summary: PromptHistorySummary = Field(default_factory=PromptHistorySummary)
    build_token_stats: PromptBuildTokenStats = Field(default_factory=PromptBuildTokenStats)
