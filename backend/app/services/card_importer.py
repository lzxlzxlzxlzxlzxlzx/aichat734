import base64
import json
import struct
import zlib
from pathlib import Path
from typing import Any

from app.core.exceptions import AppError
from app.schemas.cards import (
    CharacterCardContent,
    CharacterCardCreateRequest,
    CharacterCardExtensionBlocks,
    CharacterCardImportMeta,
    CharacterCardPlayConfig,
)


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _png_chunk(chunk_type: bytes, chunk_data: bytes) -> bytes:
    length = struct.pack(">I", len(chunk_data))
    crc = struct.pack(">I", zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF)
    return length + chunk_type + chunk_data + crc


class CharacterCardTranscoderService:
    def build_create_request_from_file(
        self, file_path: str | Path
    ) -> CharacterCardCreateRequest:
        path = Path(file_path)
        suffix = path.suffix.lower()
        if suffix == ".png":
            raw_payload = self.load_sillytavern_card_from_png_bytes(path.read_bytes(), path.name)
            source_type = "imported_st_png"
            import_strategy = "sillytavern_png_text_chunk"
        elif suffix == ".json":
            raw_payload = json.loads(path.read_text(encoding="utf-8"))
            source_type = "imported_st_json"
            import_strategy = "sillytavern_json"
        else:
            raise AppError(f"Unsupported character card file: {path.name}", 400)

        return self.map_to_create_request(
            raw_payload=raw_payload,
            source_name=path.name,
            source_type=source_type,
            import_strategy=import_strategy,
        )

    def build_create_request_from_upload(
        self,
        *,
        file_name: str,
        content: bytes,
    ) -> CharacterCardCreateRequest:
        suffix = Path(file_name).suffix.lower()
        if suffix == ".png":
            raw_payload = self.load_sillytavern_card_from_png_bytes(content, file_name)
            source_type = "imported_st_png"
            import_strategy = "sillytavern_png_text_chunk"
        elif suffix == ".json":
            try:
                raw_payload = json.loads(content.decode("utf-8"))
            except UnicodeDecodeError as exc:
                raise AppError("Character card JSON must be UTF-8 encoded.", 400) from exc
            source_type = "imported_st_json"
            import_strategy = "sillytavern_json"
        else:
            raise AppError("Only .png and .json character card files are supported.", 400)

        return self.map_to_create_request(
            raw_payload=raw_payload,
            source_name=file_name,
            source_type=source_type,
            import_strategy=import_strategy,
        )

    def load_sillytavern_card_from_png_bytes(
        self, png_bytes: bytes, file_name: str = "card.png"
    ) -> dict[str, Any]:
        if len(png_bytes) < 8 or png_bytes[:8] != PNG_SIGNATURE:
            raise AppError(f"Invalid PNG file: {file_name}", 400)

        position = 8
        while position + 8 <= len(png_bytes):
            chunk_length = struct.unpack(">I", png_bytes[position : position + 4])[0]
            chunk_type = png_bytes[position + 4 : position + 8]
            chunk_data_start = position + 8
            chunk_data_end = chunk_data_start + chunk_length
            chunk_data = png_bytes[chunk_data_start:chunk_data_end]
            position = chunk_data_end + 4

            if chunk_type != b"tEXt" or not chunk_data.startswith(b"chara\x00"):
                continue

            encoded_payload = chunk_data.split(b"\x00", 1)[1]
            try:
                decoded_payload = base64.b64decode(encoded_payload)
                return json.loads(decoded_payload)
            except Exception as exc:
                raise AppError(
                    f"Unable to decode embedded character card metadata from {file_name}",
                    400,
                ) from exc

        raise AppError(f"PNG does not contain embedded 'chara' metadata: {file_name}", 400)

    def pick_value(
        self, raw_payload: dict[str, Any], key: str, default: Any = ""
    ) -> Any:
        data_block = raw_payload.get("data")
        if isinstance(data_block, dict) and key in data_block and data_block.get(key) is not None:
            return data_block.get(key)
        if raw_payload.get(key) is not None:
            return raw_payload.get(key)
        return default

    def normalize_tags(self, tags: Any) -> list[str]:
        if not isinstance(tags, list):
            return []
        return [str(tag).strip() for tag in tags if str(tag).strip()]

    def map_to_create_request(
        self,
        *,
        raw_payload: dict[str, Any],
        source_name: str,
        source_type: str,
        import_strategy: str,
    ) -> CharacterCardCreateRequest:
        unsupported_fields: list[str] = []
        data_block = raw_payload.get("data") if isinstance(raw_payload.get("data"), dict) else {}
        if data_block.get("character_book"):
            unsupported_fields.append("character_book")
        if data_block.get("group_only_greetings"):
            unsupported_fields.append("group_only_greetings")
        if raw_payload.get("avatar"):
            unsupported_fields.append("avatar")

        return CharacterCardCreateRequest(
            name=str(self.pick_value(raw_payload, "name", Path(source_name).stem)),
            description=str(self.pick_value(raw_payload, "description", "")),
            tags=self.normalize_tags(self.pick_value(raw_payload, "tags", [])),
            status="draft",
            version_label="Imported from SillyTavern card",
            spec="izumi_v1",
            source_type=source_type,
            is_published=False,
            content=CharacterCardContent(
                system_prompt=str(self.pick_value(raw_payload, "system_prompt", "")),
                post_history_instructions=str(
                    self.pick_value(raw_payload, "post_history_instructions", "")
                ),
                first_mes=str(self.pick_value(raw_payload, "first_mes", "")),
                alternate_greetings=[
                    str(item)
                    for item in self.pick_value(raw_payload, "alternate_greetings", [])
                    if str(item).strip()
                ],
                mes_example=str(self.pick_value(raw_payload, "mes_example", "")),
                scenario=str(self.pick_value(raw_payload, "scenario", "")),
                personality=str(self.pick_value(raw_payload, "personality", "")),
                speaking_style="",
                background="",
                creator_notes=str(self.pick_value(raw_payload, "creator_notes", "")),
            ),
            play_config=CharacterCardPlayConfig(),
            extension_blocks=CharacterCardExtensionBlocks(
                preset_config={
                    "creator": self.pick_value(raw_payload, "creator", ""),
                    "character_version": self.pick_value(raw_payload, "character_version", ""),
                    "spec_version": raw_payload.get("spec_version"),
                },
                image_config=data_block.get("extensions") or {},
            ),
            import_meta=CharacterCardImportMeta(
                raw_source=raw_payload,
                mapping_report={
                    "source_name": source_name,
                    "source_spec": raw_payload.get("spec"),
                    "source_spec_version": raw_payload.get("spec_version"),
                    "import_strategy": import_strategy,
                },
                unsupported_fields=unsupported_fields,
            ),
        )

    def build_sillytavern_export_payload(self, *, card, version) -> dict[str, Any]:
        prompt_blocks = version.prompt_blocks
        extension_blocks = version.extension_blocks
        import_meta = version.import_meta
        play_config = version.play_config

        payload = {
            "name": card.name,
            "description": card.description or "",
            "personality": prompt_blocks.get("personality", ""),
            "scenario": prompt_blocks.get("scenario", ""),
            "first_mes": prompt_blocks.get("first_mes", ""),
            "mes_example": prompt_blocks.get("mes_example", ""),
            "creatorcomment": prompt_blocks.get("creator_notes", ""),
            "avatar": "none",
            "talkativeness": "",
            "fav": False,
            "tags": card.tags or [],
            "spec": "chara_card_v3",
            "spec_version": "3.0",
            "data": {
                "name": card.name,
                "description": card.description or "",
                "personality": prompt_blocks.get("personality", ""),
                "scenario": prompt_blocks.get("scenario", ""),
                "first_mes": prompt_blocks.get("first_mes", ""),
                "mes_example": prompt_blocks.get("mes_example", ""),
                "creator_notes": prompt_blocks.get("creator_notes", ""),
                "system_prompt": prompt_blocks.get("system_prompt", ""),
                "post_history_instructions": prompt_blocks.get(
                    "post_history_instructions", ""
                ),
                "tags": card.tags or [],
                "creator": extension_blocks.get("preset_config", {}).get("creator", ""),
                "character_version": extension_blocks.get("preset_config", {}).get(
                    "character_version", ""
                ),
                "alternate_greetings": prompt_blocks.get("alternate_greetings", []),
                "extensions": {
                    **(extension_blocks.get("image_config") or {}),
                    "izumi_export": {
                        "card_id": card.id,
                        "version_id": version.id,
                        "worldbook_id": card.worldbook_id,
                        "default_preset_id": card.default_preset_id,
                        "play_config": play_config,
                        "import_meta": import_meta,
                    },
                },
                "group_only_greetings": [],
                "character_book": None,
            },
            "create_date": card.created_at.isoformat(),
        }
        return payload

    def export_json_bytes(self, *, payload: dict[str, Any]) -> bytes:
        return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

    def export_png_bytes(self, *, payload: dict[str, Any]) -> bytes:
        encoded_payload = base64.b64encode(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        )
        ihdr = _png_chunk(
            b"IHDR",
            struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0),
        )
        text = _png_chunk(b"tEXt", b"chara\x00" + encoded_payload)
        idat = _png_chunk(
            b"IDAT",
            zlib.compress(b"\x00\xff\xff\xff"),
        )
        iend = _png_chunk(b"IEND", b"")
        return PNG_SIGNATURE + ihdr + text + idat + iend
