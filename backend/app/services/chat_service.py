from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models import Chat


class ChatService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_chat(self, title: str) -> Chat:
        now = datetime.utcnow()
        chat = Chat(
            id=str(uuid4()),
            title=title,
            status="active",
            created_at=now,
            updated_at=now,
        )

        self.db.add(chat)
        self.db.commit()
        self.db.refresh(chat)
        return chat

    def get_chat(self, chat_id: str) -> Chat | None:
        return self.db.get(Chat, chat_id)

    def list_chats(self) -> list[Chat]:
        return self.db.query(Chat).order_by(Chat.updated_at.desc()).all()

    def update_chat(self, chat_id: str, title: str) -> Chat | None:
        chat = self.db.get(Chat, chat_id)
        if chat is None:
            return None

        chat.title = title
        chat.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(chat)
        return chat
