from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import FileResponse

from app.schemas.media import MediaAssetResponse, UploadMediaResponse
from app.services.media import MediaService

router = APIRouter(tags=["media"])

service = MediaService()


@router.post("/media/upload", response_model=UploadMediaResponse, status_code=201)
async def upload_media(
    file: UploadFile = File(...),
    category: str = Form("upload"),
) -> UploadMediaResponse:
    return service.upload_file(file=file, category=category)


@router.get("/media/{media_asset_id}", response_model=MediaAssetResponse)
async def get_media_asset(media_asset_id: str) -> MediaAssetResponse:
    return service.get_asset(media_asset_id)


@router.get("/media/{media_asset_id}/download")
async def download_media_asset(media_asset_id: str) -> FileResponse:
    return service.download_asset(media_asset_id)
