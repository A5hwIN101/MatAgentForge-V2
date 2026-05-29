# backend/app/schemas/chat.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ChatCreate(BaseModel):
    title: str

class Chat(BaseModel):
    id: str
    title: str
    status: str
    created_at: datetime
    updated_at: datetime

class ChatPreview(Chat):
    last_material_formula: Optional[str] = None
    last_verdict: Optional[str] = None

class ChatDetail(Chat):
    items: list = []

class ChatItem(BaseModel):
    id: str
    chat_id: str
    type: str
    content: str
    created_at: datetime
