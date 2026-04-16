import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_DB_PATH = PROJECT_ROOT / "data" / "test_f3_creation_flow.sqlite"
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
        create_project_response = client.post(
            "/v1/creation/projects",
            json={
                "name": "Manual Creation Project",
                "description": "for f3 project api",
                "project_type": "adaptation",
                "ip_name": "Test IP",
                "status": "active",
                "default_model": "mock-project-model",
            },
        )
        _assert(
            create_project_response.status_code == 201,
            "create creation project failed",
        )
        manual_project = create_project_response.json()

        projects_response = client.get("/v1/creation/projects")
        _assert(projects_response.status_code == 200, "list creation projects failed")
        _assert(
            any(item["id"] == manual_project["id"] for item in projects_response.json()),
            "manual project missing from list",
        )

        create_card_response = client.post(
            "/v1/creation/cards",
            json={
                "name": "Creation Test Card",
                "description": "for f3 flow",
                "tags": ["creation", "test"],
                "status": "draft",
                "is_published": False,
                "content": {
                    "first_mes": "",
                    "scenario": "创作模式测试场景",
                    "personality": "理性、适合共创",
                    "creator_notes": "先搭创作模式骨架",
                },
            },
        )
        _assert(
            create_card_response.status_code in {200, 201},
            "create creation card failed",
        )
        card = create_card_response.json()
        card_id = card["id"]
        auto_project_id = card["project_id"]
        _assert(auto_project_id is not None, "creation card should auto bind a project")

        auto_project_detail_response = client.get(
            f"/v1/creation/projects/{auto_project_id}"
        )
        _assert(
            auto_project_detail_response.status_code == 200,
            "get auto project detail failed",
        )
        auto_project_detail = auto_project_detail_response.json()
        _assert(
            any(item["id"] == card_id for item in auto_project_detail["cards"]),
            "auto project missing created card",
        )

        list_cards_response = client.get("/v1/creation/cards")
        _assert(list_cards_response.status_code == 200, "list creation cards failed")
        cards = list_cards_response.json()
        _assert(any(item["id"] == card_id for item in cards), "created card missing")

        home_response = client.get("/v1/creation/home")
        _assert(home_response.status_code == 200, "creation home failed")
        home_payload = home_response.json()
        _assert(
            any(item["id"] == card_id for item in home_payload["cards"]),
            "creation home missing card",
        )
        _assert(
            any(item["id"] == auto_project_id for item in home_payload["projects"]),
            "creation home missing auto project",
        )

        detail_response = client.get(f"/v1/creation/cards/{card_id}")
        _assert(detail_response.status_code == 200, "get creation card detail failed")
        detail = detail_response.json()
        _assert(detail["card"]["id"] == card_id, "creation card detail mismatch")

        create_session_response = client.post(
            f"/v1/creation/cards/{card_id}/sessions",
            json={"model_name": "mock-creation-model"},
        )
        _assert(
            create_session_response.status_code == 201,
            "create creation session failed",
        )
        session = create_session_response.json()
        session_id = session["id"]
        _assert(session["mode"] == "creation", "creation session mode mismatch")

        list_sessions_response = client.get(f"/v1/creation/cards/{card_id}/sessions")
        _assert(
            list_sessions_response.status_code == 200,
            "list creation sessions failed",
        )
        _assert(
            any(item["id"] == session_id for item in list_sessions_response.json()),
            "created creation session missing",
        )

        overview_response = client.get(f"/v1/creation/sessions/{session_id}/overview")
        _assert(
            overview_response.status_code == 200,
            "get creation session overview failed",
        )
        overview = overview_response.json()
        _assert(overview["session"]["id"] == session_id, "overview session mismatch")
        _assert(overview["card"]["id"] == card_id, "overview card mismatch")

        send_response = client.post(
            f"/v1/sessions/{session_id}/messages",
            json={"content": "请帮我把这个角色卡的设定扩成三个章节的大纲。"},
        )
        _assert(send_response.status_code == 201, "send creation message failed")
        sent_payload = send_response.json()
        user_message_id = sent_payload["user_message"]["id"]

        quick_replies_response = client.get(
            f"/v1/creation/sessions/{session_id}/quick-replies"
        )
        _assert(
            quick_replies_response.status_code == 200,
            "creation quick replies failed",
        )

        traces_response = client.get(f"/v1/creation/sessions/{session_id}/traces")
        _assert(traces_response.status_code == 200, "creation traces list failed")
        trace_items = traces_response.json()["items"]
        _assert(len(trace_items) >= 1, "creation traces missing")
        trace_id = trace_items[0]["id"]

        latest_trace_response = client.get(
            f"/v1/creation/sessions/{session_id}/traces/latest"
        )
        _assert(latest_trace_response.status_code == 200, "latest creation trace failed")

        trace_response = client.get(
            f"/v1/creation/sessions/{session_id}/traces/{trace_id}"
        )
        _assert(trace_response.status_code == 200, "creation trace by id failed")

        message_trace_response = client.get(
            f"/v1/creation/sessions/{session_id}/messages/{user_message_id}/trace"
        )
        _assert(
            message_trace_response.status_code == 200,
            "creation message trace failed",
        )

        rename_response = client.patch(
            f"/v1/creation/sessions/{session_id}/rename",
            json={"name": "角色卡创作工作台"},
        )
        _assert(rename_response.status_code == 200, "rename creation session failed")
        _assert(rename_response.json()["name"] == "角色卡创作工作台", "rename mismatch")

        model_response = client.patch(
            f"/v1/creation/sessions/{session_id}/model",
            json={"model_name": "mock-creation-v2"},
        )
        _assert(model_response.status_code == 200, "switch creation model failed")
        _assert(
            model_response.json()["model_name"] == "mock-creation-v2",
            "creation model mismatch",
        )

        copy_response = client.post(
            f"/v1/creation/sessions/{session_id}/copy",
            json={"name": "角色卡创作工作台 - 副本"},
        )
        _assert(copy_response.status_code == 201, "copy creation session failed")
        copied_session_id = copy_response.json()["session"]["id"]
        _assert(copied_session_id != session_id, "copied session id should differ")

        export_response = client.get(
            f"/v1/creation/sessions/{session_id}/export",
            params={"export_format": "markdown", "export_scope": "debug"},
        )
        _assert(export_response.status_code == 200, "export creation session failed")
        _assert(
            "Prompt Trace Summary" in export_response.json()["content"],
            "creation export missing trace summary",
        )

        reuse_response = client.post(
            f"/v1/creation/cards/{card_id}/sessions",
            json={"use_latest_existing_session": True},
        )
        _assert(reuse_response.status_code == 201, "reuse creation session failed")
        _assert(
            reuse_response.json()["id"] == copied_session_id,
            "reuse session mismatch",
        )

        update_card_response = client.put(
            f"/v1/creation/cards/{card_id}",
            json={
                "name": "Creation Test Card V2",
                "description": "updated in f3 flow",
                "tags": ["creation", "test", "updated"],
                "status": "draft",
                "is_published": False,
                "content": {
                    "first_mes": "",
                    "scenario": "创作模式测试场景升级版",
                    "personality": "更完整的人设轮廓",
                    "creator_notes": "加入大纲和章节拆分",
                },
            },
        )
        _assert(update_card_response.status_code == 200, "update creation card failed")
        updated_card = update_card_response.json()
        _assert(updated_card["name"] == "Creation Test Card V2", "updated card name mismatch")

        update_project_response = client.put(
            f"/v1/creation/projects/{manual_project['id']}",
            json={
                "name": "Manual Creation Project V2",
                "description": "updated project",
                "project_type": "original",
                "ip_name": None,
                "status": "archived",
                "default_model": "mock-project-model-v2",
            },
        )
        _assert(update_project_response.status_code == 200, "update project failed")
        _assert(
            update_project_response.json()["status"] == "archived",
            "project update mismatch",
        )

        archive_response = client.patch(
            f"/v1/creation/sessions/{session_id}/status",
            json={"status": "archived"},
        )
        _assert(archive_response.status_code == 200, "archive creation session failed")
        _assert(archive_response.json()["status"] == "archived", "creation archive mismatch")

        print("F3 creation flow test passed")
        print(f"card_id={card_id}")
        print(f"session_id={session_id}")
        print(f"trace_count={len(trace_items)}")


if __name__ == "__main__":
    main()
