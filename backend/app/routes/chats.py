from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.chat import Chat, ChatCreate, ChatDetail, ChatPreview
from app.services.chat_service import ChatService

router = APIRouter(prefix="/api/chats", tags=["chats"])


def get_chat_service(db: Annotated[Session, Depends(get_db)]) -> ChatService:
    return ChatService(db)


@router.post("", response_model=Chat)
def create_chat(
    payload: ChatCreate,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> Chat:
    chat = service.create_chat(payload.title)
    return Chat.model_validate(chat, from_attributes=True)


@router.get("", response_model=list[ChatPreview])
def list_chats(
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> list[ChatPreview]:
    chats = service.list_chats()
    return [ChatPreview.model_validate(chat, from_attributes=True) for chat in chats]


@router.get("/{chat_id}", response_model=ChatDetail)
def get_chat(
    chat_id: str,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatDetail:
    chat = service.get_chat(chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    return ChatDetail(
        id=chat.id,
        title=chat.title,
        status=chat.status,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        items=[],
    )


@router.put("/{chat_id}", response_model=Chat)
def update_chat(
    chat_id: str,
    payload: ChatCreate,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> Chat:
    chat = service.update_chat(chat_id, payload.title)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    return Chat.model_validate(chat, from_attributes=True)
