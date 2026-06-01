from collections.abc import Generator
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.graph.workflow import ModelRateLimitError
from app.db.database import Base, get_db
from app.main import app
from app.routes import screen as screen_route_module
from app.services.chat_service import ChatService


def build_test_client(tmp_path: Path) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "test_chat_routes.db"
    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_clear_chats_route(tmp_path: Path) -> None:
    for client in build_test_client(tmp_path):
        create_first = client.post("/api/chats", json={"title": "New Chat"})
        create_second = client.post("/api/chats", json={"title": "Old Chat"})
        assert create_first.status_code == 200
        assert create_second.status_code == 200

        response = client.delete("/api/chats")

        assert response.status_code == 200
        assert response.json() == {"deleted_count": 2, "status": "cleared"}


def test_list_chats_route_hides_empty_chats(tmp_path: Path) -> None:
    for client in build_test_client(tmp_path):
        create_real = client.post("/api/chats", json={"title": "LiCoO2"})
        create_empty = client.post("/api/chats", json={"title": "New Chat"})
        assert create_real.status_code == 200
        assert create_empty.status_code == 200

        chat_id = create_real.json()["id"]
        for db in app.dependency_overrides[get_db]():
            service = ChatService(db)
            service.append_item(chat_id, "user_message", "LiCoO2")

        response = client.get("/api/chats")

        assert response.status_code == 200
        payload = response.json()
        assert len(payload) == 1
        assert payload[0]["title"] == "LiCoO2"
        assert payload[0]["last_material_formula"] == "LiCoO2"


def test_screen_route_returns_clean_model_rate_limit_error(
    tmp_path: Path,
    monkeypatch,
) -> None:
    async def fake_run_screening_workflow(**kwargs):
        raise ModelRateLimitError(0.5)

    monkeypatch.setattr(screen_route_module, "run_screening_workflow", fake_run_screening_workflow)

    for client in build_test_client(tmp_path):
        create_chat = client.post("/api/chats", json={"title": "Rate Limited"})
        assert create_chat.status_code == 200
        chat_id = create_chat.json()["id"]

        response = client.post(f"/api/chats/{chat_id}/screen", json={"formula": "LiCoO2"})

        assert response.status_code == 200
        payloads = [
            line.removeprefix("data: ")
            for line in response.text.splitlines()
            if line.startswith("data: ")
        ]
        assert len(payloads) >= 2
        failed_payload = payloads[-1]
        assert '"event": "screen.failed"' in failed_payload
        assert '"code": "model_rate_limited"' in failed_payload
        assert '"title": "Model rate limit reached"' in failed_payload

        detail_response = client.get(f"/api/chats/{chat_id}")
        assert detail_response.status_code == 200
        item_types = [item["type"] for item in detail_response.json()["items"]]
        assert item_types == ["user_message", "error_card"]
