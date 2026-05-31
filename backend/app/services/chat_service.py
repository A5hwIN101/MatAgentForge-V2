from datetime import datetime
import json
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models import Chat, ChatItem


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

    def list_chats(self, include_empty: bool = False) -> list[Chat]:
        query = self.db.query(Chat)
        if not include_empty:
            query = query.filter(Chat.items.any())

        return query.order_by(Chat.updated_at.desc()).all()

    def update_chat(self, chat_id: str, title: str) -> Chat | None:
        chat = self.db.get(Chat, chat_id)
        if chat is None:
            return None

        chat.title = title
        chat.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(chat)
        return chat

    def append_item(self, chat_id: str, item_type: str, content: str | dict) -> ChatItem | None:
        chat = self.db.get(Chat, chat_id)
        if chat is None:
            return None

        serialized_content = json.dumps(content) if isinstance(content, dict) else content
        item = ChatItem(
            id=f"chat_item_{uuid4()}",
            chat_id=chat_id,
            type=item_type,
            content=serialized_content,
            created_at=datetime.utcnow(),
        )
        chat.updated_at = datetime.utcnow()
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def touch_chat_for_material(self, chat_id: str, formula: str) -> Chat | None:
        chat = self.db.get(Chat, chat_id)
        if chat is None:
            return None

        chat.title = formula
        chat.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(chat)
        return chat

    def clear_chats(self) -> int:
        chats = self.db.query(Chat).all()
        deleted_count = len(chats)
        for chat in chats:
            self.db.delete(chat)
        self.db.commit()
        return deleted_count
