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
    chat_one = service.create_chat("Chat One")
    chat_two = service.create_chat("Chat Two")
    chat_three = service.create_chat("Chat Three")
    service.append_item(chat_one.id, "user_message", "LiCoO2")
    service.append_item(chat_two.id, "user_message", "LiFePO4")
    service.append_item(chat_three.id, "user_message", "NMC")

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


def test_list_chats_hides_empty_entries(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    empty_chat = service.create_chat("New Chat")
    real_chat = service.create_chat("LiCoO2")
    service.append_item(real_chat.id, "user_message", "LiCoO2")

    chats = service.list_chats()

    assert len(chats) == 1
    assert chats[0].id == real_chat.id
    assert chats[0].id != empty_chat.id


def test_clear_chats(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    first_chat = service.create_chat("Chat One")
    second_chat = service.create_chat("Chat Two")
    service.append_item(first_chat.id, "user_message", "LiCoO2")
    service.append_item(second_chat.id, "user_message", "LiFePO4")

    deleted_count = service.clear_chats()

    assert deleted_count == 2
    assert service.list_chats(include_empty=True) == []
