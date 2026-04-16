import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_DB_PATH = PROJECT_ROOT / "data" / "test_f2_chat_flow.sqlite"
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
                "name": "Reference Card",
                "description": "used by F2 chat flow",
                "tags": ["chat", "reference"],
                "status": "published",
                "is_published": True,
                "content": {
                    "first_mes": "你好，我是一个用于聊天模式引用的角色卡。",
                    "scenario": "聊天模式引用测试",
                    "personality": "冷静、理性、适合分析",
                    "speaking_style": "简洁直接",
                    "background": "来自测试数据",
                },
            },
        )
        _assert(create_card_response.status_code in {200, 201}, "create reference card failed")
        card_id = create_card_response.json()["id"]

        create_chat_response = client.post(
            "/v1/chat/sessions",
            json={"name": "新聊天"},
        )
        _assert(create_chat_response.status_code == 201, "create chat session failed")
        chat_session = create_chat_response.json()
        session_id = chat_session["id"]
        _assert(chat_session["mode"] == "chat", "chat session mode mismatch")

        send_response = client.post(
            f"/v1/sessions/{session_id}/messages",
            json={
                "content": "帮我分析一下这个角色卡的人设风格和聊天适配性",
                "references": [
                    {
                        "reference_type": "card",
                        "target_id": card_id,
                        "label": "Reference Card",
                    }
                ],
            },
        )
        _assert(send_response.status_code == 201, "send chat message failed")
        sent_payload = send_response.json()
        user_message_id = sent_payload["user_message"]["id"]
        assistant_message_id = sent_payload["assistant_message"]["id"]

        renamed_session_response = client.get(f"/v1/chat/sessions/{session_id}/overview")
        _assert(renamed_session_response.status_code == 200, "chat overview failed after send")
        renamed_session = renamed_session_response.json()["session"]
        _assert(
            renamed_session["name"] == "帮我分析一下这个角色卡的人设风格和聊天适配性",
            "chat session auto rename failed",
        )

        model_response = client.patch(
            f"/v1/chat/sessions/{session_id}/model",
            json={"model_name": "mock-chat-advanced"},
        )
        _assert(model_response.status_code == 200, "switch chat model failed")
        _assert(model_response.json()["model_name"] == "mock-chat-advanced", "model switch mismatch")

        traces_response = client.get(f"/v1/chat/sessions/{session_id}/traces")
        _assert(traces_response.status_code == 200, "chat traces list failed")
        trace_items = traces_response.json()["items"]
        _assert(len(trace_items) >= 1, "chat traces empty")
        trace_id = trace_items[0]["id"]

        trace_response = client.get(f"/v1/chat/sessions/{session_id}/traces/{trace_id}")
        _assert(trace_response.status_code == 200, "get chat trace failed")
        trace_payload = trace_response.json()
        _assert(trace_payload["message_id"] == user_message_id, "trace message binding mismatch")
        _assert(
            any(item["source_type"] == "chat_reference_card" for item in trace_payload["injection_items"]),
            "card reference injection missing from trace",
        )

        regenerate_response = client.post(
            f"/v1/messages/{assistant_message_id}/regenerate",
            json={"model_name": "mock-chat-advanced"},
        )
        _assert(regenerate_response.status_code == 200, "regenerate assistant message failed")

        latest_trace_response = client.get(f"/v1/chat/sessions/{session_id}/traces/latest")
        _assert(latest_trace_response.status_code == 200, "latest chat trace failed")
        latest_trace_payload = latest_trace_response.json()
        _assert(
            any(item["source_type"] == "chat_reference_card" for item in latest_trace_payload["injection_items"]),
            "card reference injection missing after regenerate",
        )

        print("F2 chat flow test passed")
        print(f"chat_session_id={session_id}")
        print(f"user_message_id={user_message_id}")
        print(f"assistant_message_id={assistant_message_id}")


if __name__ == "__main__":
    main()
