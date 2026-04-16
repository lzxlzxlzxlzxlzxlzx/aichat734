import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_DB_PATH = PROJECT_ROOT / "data" / "test_f1_play_flow.sqlite"
BACKEND_ROOT = PROJECT_ROOT / "backend"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ["DATABASE_PATH"] = str(TEST_DB_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/")
os.environ["ENABLE_MOCK_FALLBACK"] = "1"

if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

from fastapi.testclient import TestClient

from app.main import app


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    with TestClient(app) as client:
        create_card_response = client.post(
            "/v1/cards",
            json={
                "name": "Play Test Card",
                "description": "for f1 flow",
                "tags": ["play", "test"],
                "status": "published",
                "is_published": True,
                "content": {
                    "first_mes": "雨夜里，角色先开口：你终于来了。",
                    "alternate_greetings": [
                        "清晨时，角色轻声说：今天想从哪里开始？"
                    ],
                    "scenario": "测试场景",
                    "personality": "沉稳",
                },
            },
        )
        _assert(create_card_response.status_code == 200 or create_card_response.status_code == 201, "create card failed")
        card = create_card_response.json()
        card_id = card["id"]

        list_play_cards_response = client.get("/v1/play/cards")
        _assert(list_play_cards_response.status_code == 200, "list play cards failed")
        play_cards = list_play_cards_response.json()
        _assert(any(item["id"] == card_id for item in play_cards), "published card missing in play cards")

        detail_response = client.get(f"/v1/play/cards/{card_id}")
        _assert(detail_response.status_code == 200, "get play card detail failed")
        detail = detail_response.json()
        _assert(len(detail["openings"]) == 2, "openings not resolved correctly")

        create_play_session_response = client.post(
            f"/v1/play/cards/{card_id}/sessions",
            json={
                "name": "我的第一条剧情线",
                "opening_index": 1,
            },
        )
        _assert(create_play_session_response.status_code == 201, "create play session failed")
        play_session = create_play_session_response.json()
        session_id = play_session["session"]["id"]
        opening_message_id = play_session["opening_message_id"]
        _assert(opening_message_id is not None, "opening message not created")

        session_messages_response = client.get(f"/v1/sessions/{session_id}/messages")
        _assert(session_messages_response.status_code == 200, "list session messages failed")
        session_messages = session_messages_response.json()
        _assert(len(session_messages) == 1, "opening message count mismatch")
        _assert(session_messages[0]["source_type"] == "opening", "opening source_type mismatch")
        opening_message_id_from_list = session_messages[0]["id"]

        lock_response = client.patch(
            f"/v1/messages/{opening_message_id_from_list}/lock",
            json={"is_locked": True},
        )
        _assert(lock_response.status_code == 200, "lock message failed")
        _assert(lock_response.json()["is_locked"] is True, "lock state mismatch")

        session_list_response = client.get(f"/v1/play/cards/{card_id}/sessions")
        _assert(session_list_response.status_code == 200, "list play sessions failed")
        session_list = session_list_response.json()
        _assert(any(item["id"] == session_id for item in session_list), "created play session missing")

        overview_response = client.get(f"/v1/play/sessions/{session_id}/overview")
        _assert(overview_response.status_code == 200, "get play session overview failed")
        overview = overview_response.json()
        _assert(overview["session"]["id"] == session_id, "overview session mismatch")
        _assert(overview["card"]["id"] == card_id, "overview card mismatch")

        rename_response = client.patch(
            f"/v1/play/sessions/{session_id}/rename",
            json={"name": "改名后的剧情线"},
        )
        _assert(rename_response.status_code == 200, "rename play session failed")
        _assert(rename_response.json()["name"] == "改名后的剧情线", "rename did not persist")

        export_response = client.get(
            f"/v1/play/sessions/{session_id}/export",
            params={"export_format": "markdown", "export_scope": "reader"},
        )
        _assert(export_response.status_code == 200, "export play session failed")
        _assert("改名后的剧情线" in export_response.json()["content"], "export content missing session name")

        reuse_response = client.post(
            f"/v1/play/cards/{card_id}/sessions",
            json={
                "name": "忽略这个名字",
                "use_latest_existing_session": True,
            },
        )
        _assert(reuse_response.status_code == 201, "reuse latest session failed")
        reused = reuse_response.json()
        _assert(reused["session"]["id"] == session_id, "latest session reuse mismatch")

        archive_response = client.patch(
            f"/v1/play/sessions/{session_id}/status",
            json={"status": "archived"},
        )
        _assert(archive_response.status_code == 200, "archive play session failed")
        _assert(archive_response.json()["status"] == "archived", "archive status mismatch")

        snapshots_response = client.get(f"/v1/play/sessions/{session_id}/snapshots")
        _assert(snapshots_response.status_code == 200, "list play snapshots failed")

        send_response = client.post(
            f"/v1/sessions/{session_id}/messages",
            json={"content": "记住：今晚下雨，我们在旧车站见面。"},
        )
        _assert(send_response.status_code == 201, "play session send failed")
        sent_payload = send_response.json()
        user_message_id = sent_payload["user_message"]["id"]

        state_bundle_response = client.get(f"/v1/play/sessions/{session_id}/state")
        _assert(state_bundle_response.status_code == 200, "play state bundle failed")

        traces_response = client.get(f"/v1/play/sessions/{session_id}/traces")
        _assert(traces_response.status_code == 200, "play traces list failed")
        _assert(len(traces_response.json()["items"]) >= 1, "play traces missing")

        latest_trace_response = client.get(
            f"/v1/play/sessions/{session_id}/traces/latest"
        )
        _assert(latest_trace_response.status_code == 200, "play latest trace failed")

        message_trace_response = client.get(
            f"/v1/play/sessions/{session_id}/messages/{user_message_id}/trace"
        )
        _assert(message_trace_response.status_code == 200, "play message trace failed")

        print("F1 play flow test passed")
        print(f"card_id={card_id}")
        print(f"session_id={session_id}")
        print(f"opening_count={len(detail['openings'])}")


if __name__ == "__main__":
    main()
