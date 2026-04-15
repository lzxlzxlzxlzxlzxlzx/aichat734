from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CharacterCardContent(BaseModel):
    system_prompt: str = ""
    post_history_instructions: str = ""
    first_mes: str = ""
    alternate_greetings: list[str] = Field(default_factory=list)
    mes_example: str = ""
    scenario: str = ""
    personality: str = ""
    speaking_style: str = ""
    background: str = ""
    creator_notes: str = ""


class CharacterCardPlayConfig(BaseModel):
    worldbook_id: str | None = None
    default_model: str | None = None
    default_temperature: float | None = None
    default_max_tokens: int | None = None
    allow_multimodal_input: bool = True


class CharacterCardExtensionBlocks(BaseModel):
    depth_prompt: dict[str, Any] = Field(default_factory=dict)
    authors_note: dict[str, Any] = Field(default_factory=dict)
    preset_config: dict[str, Any] = Field(default_factory=dict)
    image_config: dict[str, Any] = Field(default_factory=dict)
    regex_script_ids: list[str] = Field(default_factory=list)
    quick_reply_set_ids: list[str] = Field(default_factory=list)
    npcs: list[dict[str, Any]] = Field(default_factory=list)


class CharacterCardImportMeta(BaseModel):
    raw_source: dict[str, Any] = Field(default_factory=dict)
    mapping_report: dict[str, Any] = Field(default_factory=dict)
    unsupported_fields: list[str] = Field(default_factory=list)


class CharacterCardBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    project_id: str | None = None
    worldbook_id: str | None = None
    default_preset_id: str | None = None
    cover_asset_id: str | None = None
    avatar_asset_id: str | None = None
    tags: list[str] = Field(default_factory=list)


class CharacterCardCreateRequest(CharacterCardBase):
    status: str = Field(default="draft")
    version_label: str | None = None
    spec: str = Field(default="izumi_v1")
    source_type: str = Field(default="created")
    is_published: bool = False
    content: CharacterCardContent = Field(default_factory=CharacterCardContent)
    play_config: CharacterCardPlayConfig = Field(default_factory=CharacterCardPlayConfig)
    extension_blocks: CharacterCardExtensionBlocks = Field(default_factory=CharacterCardExtensionBlocks)
    import_meta: CharacterCardImportMeta = Field(default_factory=CharacterCardImportMeta)


class CharacterCardUpdateRequest(CharacterCardCreateRequest):
    pass


class CharacterCardVersionResponse(BaseModel):
    id: str
    card_id: str
    version: int
    version_label: str | None = None
    is_published: bool
    spec: str
    source_type: str
    base_info: dict[str, Any]
    prompt_blocks: dict[str, Any]
    play_config: dict[str, Any]
    extension_blocks: dict[str, Any]
    import_meta: dict[str, Any]
    created_at: datetime


class CharacterCardResponse(BaseModel):
    id: str
    project_id: str | None = None
    name: str
    name_normalized: str
    description: str | None = None
    tags: list[str]
    cover_asset_id: str | None = None
    avatar_asset_id: str | None = None
    worldbook_id: str | None = None
    default_preset_id: str | None = None
    status: str
    source_type: str
    current_draft_version_id: str | None = None
    current_published_version_id: str | None = None
    latest_session_id: str | None = None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None
    current_version: CharacterCardVersionResponse | None = None
