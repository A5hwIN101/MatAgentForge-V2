from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import Base
from app.services.chat_service import ChatService


def build_service(tmp_path: Path) -> ChatService:
    db_path = tmp_path / "test_chat_service.db"
    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db: Session = TestingSessionLocal()
    return ChatService(db)


def test_create_chat(tmp_path: Path) -> None:
    service = build_service(tmp_path)

    chat = service.create_chat("Cathode Screen")

    assert chat.id
    assert chat.title == "Cathode Screen"
    assert chat.created_at is not None
    assert chat.updated_at is not None


def test_get_chat(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    created_chat = service.create_chat("Anode Review")

    fetched_chat = service.get_chat(created_chat.id)

    assert fetched_chat is not None
    assert fetched_chat.id == created_chat.id
    assert fetched_chat.title == "Anode Review"


def test_list_chats(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    service.create_chat("Chat One")
    service.create_chat("Chat Two")
    service.create_chat("Chat Three")

    chats = service.list_chats()

    assert len(chats) == 3
    assert {chat.title for chat in chats} == {"Chat One", "Chat Two", "Chat Three"}


def test_update_chat(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    created_chat = service.create_chat("Original Title")

    updated_chat = service.update_chat(created_chat.id, "Updated Title")

    assert updated_chat is not None
    assert updated_chat.title == "Updated Title"

    fetched_chat = service.get_chat(created_chat.id)
    assert fetched_chat is not None
    assert fetched_chat.title == "Updated Title"


def test_get_nonexistent_chat(tmp_path: Path) -> None:
    service = build_service(tmp_path)

    chat = service.get_chat("missing-chat-id")

    assert chat is None
