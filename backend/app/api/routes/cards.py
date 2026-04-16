from fastapi import APIRouter, File, UploadFile
from fastapi.responses import StreamingResponse

from app.schemas.cards import (
    CharacterCardCreateRequest,
    CharacterCardResponse,
    CharacterCardUpdateRequest,
)
from app.services.cards import CardService

router = APIRouter(prefix="/cards", tags=["cards"])

service = CardService()


@router.get("", response_model=list[CharacterCardResponse])
async def list_cards() -> list[CharacterCardResponse]:
    return service.list_cards()


@router.get("/{card_id}", response_model=CharacterCardResponse)
async def get_card(card_id: str) -> CharacterCardResponse:
    return service.get_card(card_id)


@router.post("", response_model=CharacterCardResponse, status_code=201)
async def create_card(payload: CharacterCardCreateRequest) -> CharacterCardResponse:
    return service.create_card(payload)


@router.post("/import", response_model=CharacterCardResponse, status_code=201)
async def import_card(file: UploadFile = File(...)) -> CharacterCardResponse:
    return service.import_card(file)


@router.put("/{card_id}", response_model=CharacterCardResponse)
async def update_card(
    card_id: str, payload: CharacterCardUpdateRequest
) -> CharacterCardResponse:
    return service.update_card(card_id, payload)


@router.get("/{card_id}/export/json")
async def export_card_json(card_id: str) -> StreamingResponse:
    return service.export_card_json(card_id)


@router.get("/{card_id}/export/png")
async def export_card_png(card_id: str) -> StreamingResponse:
    return service.export_card_png(card_id)
