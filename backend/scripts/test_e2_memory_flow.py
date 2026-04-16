import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_DB_PATH = PROJECT_ROOT / "data" / "test_e2_memory_flow.sqlite"
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
        create_session_response = client.post(
            "/v1/sessions",
            json={
                "mode": "chat",
                "name": "E2 Memory Flow Test",
            },
        )
        _assert(create_session_response.status_code == 201, "create session failed")
        session = create_session_response.json()
        session_id = session["id"]

        send_one = client.post(
            f"/v1/sessions/{session_id}/messages",
            json={
                "content": "记住：我叫林舟，我喜欢慢节奏、长篇、带细节的互动，希望你以后都按这个偏好来。",
            },
        )
        _assert(send_one.status_code == 201, "first send failed")
        first_payload = send_one.json()
        assistant_message_id = first_payload["assistant_message"]["id"]

        list_session_memories = client.get(
            f"/v1/sessions/{session_id}/long-term-memories",
            params={"scope_type": "session", "scope_id": session_id},
        )
        _assert(list_session_memories.status_code == 200, "list memories failed")
        auto_memories = list_session_memories.json()
        _assert(len(auto_memories) >= 1, "auto extraction did not create memory")
        first_auto_id = auto_memories[0]["id"]

        update_memory_response = client.patch(
            f"/v1/sessions/{session_id}/long-term-memories/{first_auto_id}",
            json={
                "content": "用户长期偏好：慢节奏、长篇、细节丰富的互动。",
                "importance": "high",
            },
        )
        _assert(update_memory_response.status_code == 200, "update memory failed")

        mark_message_response = client.post(
            f"/v1/messages/{assistant_message_id}/long-term-memory",
            json={
                "content": "助手已经确认用户偏好为慢节奏、长篇、细节丰富的互动风格。",
                "scope_type": "session",
                "importance": "high",
            },
        )
        _assert(mark_message_response.status_code == 201, "manual mark failed")

        send_two = client.post(
            f"/v1/sessions/{session_id}/messages",
            json={
                "content": "现在请根据你记住的设定，继续和我聊天，并简短说明你记住了什么。",
            },
        )
        _assert(send_two.status_code == 201, "second send failed")
        second_payload = send_two.json()
        second_user_message_id = second_payload["user_message"]["id"]

        latest_trace = client.get(f"/v1/messages/{second_user_message_id}/trace")
        _assert(latest_trace.status_code == 200, "fetch latest trace failed")
        trace = latest_trace.json()
        injection_items = trace["injection_items"]
        long_term_items = [
            item for item in injection_items if item.get("source_type") == "long_term_memory"
        ]
        _assert(len(long_term_items) >= 1, "prompt did not inject long-term memory")

        regenerate_response = client.post(
            f"/v1/messages/{second_payload['assistant_message']['id']}/regenerate",
            json={},
        )
        _assert(regenerate_response.status_code == 200, "regenerate failed")

        rollback_response = client.post(
            f"/v1/sessions/{session_id}/messages/{second_payload['assistant_message']['id']}/rollback"
        )
        _assert(rollback_response.status_code == 200, "rollback failed")

        print("E2 memory flow test passed")
        print(f"session_id={session_id}")
        final_memories = client.get(
            f"/v1/sessions/{session_id}/long-term-memories",
            params={"scope_type": "session", "scope_id": session_id},
        ).json()
        print(f"memory_count={len(final_memories)}")
        print(f"long_term_injection_count={len(long_term_items)}")


if __name__ == "__main__":
    main()
