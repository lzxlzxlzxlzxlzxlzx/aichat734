import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_DB_PATH = PROJECT_ROOT / "data" / "test_card_import_export.sqlite"
BACKEND_ROOT = PROJECT_ROOT / "backend"
CARD_FILE = PROJECT_ROOT / "ReZero_V2.2.png"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ["DATABASE_PATH"] = str(TEST_DB_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/")

if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

from fastapi.testclient import TestClient

from app.main import app
from app.services.card_importer import CharacterCardTranscoderService


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    transcoder = CharacterCardTranscoderService()

    with TestClient(app) as client:
        with CARD_FILE.open("rb") as file_handle:
            import_response = client.post(
                "/v1/cards/import",
                files={"file": (CARD_FILE.name, file_handle, "image/png")},
            )
        _assert(import_response.status_code == 201, "real card import failed")
        card = import_response.json()
        card_id = card["id"]

        _assert(card["name"] == "ReZero 从零开始的异世界生活", "imported card name mismatch")
        _assert(
            card["current_version"]["prompt_blocks"]["first_mes"],
            "first message missing after import",
        )

        export_json_response = client.get(f"/v1/cards/{card_id}/export/json")
        _assert(export_json_response.status_code == 200, "export json failed")
        exported_json = json.loads(export_json_response.content.decode("utf-8"))
        _assert(exported_json["spec"] == "chara_card_v3", "exported json spec mismatch")
        _assert(exported_json["name"] == card["name"], "exported json name mismatch")

        export_png_response = client.get(f"/v1/cards/{card_id}/export/png")
        _assert(export_png_response.status_code == 200, "export png failed")
        reparsed_payload = transcoder.load_sillytavern_card_from_png_bytes(
            export_png_response.content,
            "roundtrip.png",
        )
        _assert(reparsed_payload["name"] == card["name"], "roundtrip png name mismatch")
        _assert(
            reparsed_payload["data"]["first_mes"] == card["current_version"]["prompt_blocks"]["first_mes"],
            "roundtrip png first message mismatch",
        )

        print("Character card import/export test passed")
        print(f"card_id={card_id}")
        print(f"name={card['name']}")
        print(f"exported_json_bytes={len(export_json_response.content)}")
        print(f"exported_png_bytes={len(export_png_response.content)}")


if __name__ == "__main__":
    main()
