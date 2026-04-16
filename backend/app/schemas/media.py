from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MediaAssetResponse(BaseModel):
    id: str
    media_type: str
    category: str
    file_name: str
    file_path: str
    mime_type: str
    size_bytes: int
    meta: dict[str, Any]
    created_at: datetime
    download_url: str


class UploadMediaResponse(BaseModel):
    asset: MediaAssetResponse


class MessageAttachmentResponse(BaseModel):
    id: str
    message_id: str
    media_asset_id: str
    attachment_type: str
    order_index: int
    caption: str | None = None
    created_at: datetime
    asset: MediaAssetResponse


class MessageAttachmentBindRequest(BaseModel):
    media_asset_id: str
    attachment_type: str = Field(
        pattern="^(input_image|input_document|generated_image)$"
    )
    caption: str | None = None
    order_index: int | None = None
