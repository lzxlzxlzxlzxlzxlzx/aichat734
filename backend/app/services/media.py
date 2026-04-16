import json
import mimetypes
import re
from pathlib import Path

from fastapi import UploadFile
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.core.database import get_connection
from app.core.exceptions import AppError, NotFoundError
from app.core.ids import new_id
from app.core.time import utc_now_iso
from app.repositories.media import MediaRepository
from app.schemas.media import MediaAssetResponse, UploadMediaResponse


ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
ALLOWED_DOCUMENT_EXTENSIONS = {
    ".txt",
    ".md",
    ".pdf",
    ".doc",
    ".docx",
    ".rtf",
}


def _sanitize_file_name(file_name: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", file_name or "upload")
    return sanitized[:120] or "upload"


def _detect_media_type(file_name: str, mime_type: str | None) -> str:
    extension = Path(file_name).suffix.lower()
    normalized_mime = (mime_type or "").lower()
    if extension in ALLOWED_IMAGE_EXTENSIONS or normalized_mime.startswith("image/"):
        return "image"
    if extension in ALLOWED_DOCUMENT_EXTENSIONS:
        return "document"
    raise AppError("Unsupported attachment type.", status_code=400)


def _row_to_media_asset_response(row) -> MediaAssetResponse:
    meta = {}
    if row["meta"]:
        try:
            meta = json.loads(row["meta"])
        except json.JSONDecodeError:
            meta = {}
    return MediaAssetResponse(
        id=row["asset_id"] if "asset_id" in row.keys() else row["id"],
        media_type=row["media_type"],
        category=row["category"],
        file_name=row["file_name"],
        file_path=row["file_path"],
        mime_type=row["mime_type"],
        size_bytes=row["size_bytes"],
        meta=meta,
        created_at=row["asset_created_at"] if "asset_created_at" in row.keys() else row["created_at"],
        download_url=f"/v1/media/{row['asset_id'] if 'asset_id' in row.keys() else row['id']}/download",
    )


class MediaService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def upload_file(
        self,
        *,
        file: UploadFile,
        category: str = "upload",
    ) -> UploadMediaResponse:
        if category not in {"upload", "generated", "reference", "cover", "avatar"}:
            raise AppError("Invalid media category.", status_code=400)

        original_name = file.filename or "upload.bin"
        mime_type = file.content_type or mimetypes.guess_type(original_name)[0] or "application/octet-stream"
        media_type = _detect_media_type(original_name, mime_type)
        safe_name = _sanitize_file_name(original_name)
        asset_id = new_id()
        target_dir = self.settings.resolved_uploads_dir / media_type
        target_dir.mkdir(parents=True, exist_ok=True)
        stored_name = f"{asset_id}_{safe_name}"
        target_path = target_dir / stored_name

        content = file.file.read()
        size_bytes = len(content)
        if size_bytes <= 0:
            raise AppError("Uploaded file is empty.", status_code=400)

        target_path.write_bytes(content)
        now = utc_now_iso()

        with get_connection() as connection:
            repository = MediaRepository(connection)
            repository.create_media_asset(
                {
                    "id": asset_id,
                    "media_type": media_type,
                    "category": category,
                    "file_name": original_name,
                    "file_path": str(target_path),
                    "mime_type": mime_type,
                    "size_bytes": size_bytes,
                    "meta": json.dumps(
                        {
                            "stored_name": stored_name,
                            "extension": Path(original_name).suffix.lower(),
                        },
                        ensure_ascii=False,
                    ),
                    "created_at": now,
                }
            )
            asset_row = repository.get_media_asset(asset_id)

        return UploadMediaResponse(asset=_row_to_media_asset_response(asset_row))

    def get_asset(self, media_asset_id: str) -> MediaAssetResponse:
        with get_connection() as connection:
            repository = MediaRepository(connection)
            row = repository.get_media_asset(media_asset_id)
            if row is None:
                raise NotFoundError(f"Media asset not found: {media_asset_id}")
            return _row_to_media_asset_response(row)

    def download_asset(self, media_asset_id: str) -> FileResponse:
        asset = self.get_asset(media_asset_id)
        file_path = Path(asset.file_path)
        if not file_path.exists():
            raise NotFoundError(f"Media file not found on disk: {media_asset_id}")
        return FileResponse(
            path=file_path,
            media_type=asset.mime_type,
            filename=asset.file_name,
        )
