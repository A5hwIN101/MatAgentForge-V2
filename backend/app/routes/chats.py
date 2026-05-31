import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Chat as ChatModel
from app.db.models import ChatItem as ChatItemModel
from app.schemas.chat import Chat, ChatClearResponse, ChatCreate, ChatDetail, ChatItem, ChatPreview
from app.services.chat_service import ChatService

router = APIRouter(prefix="/api/chats", tags=["chats"])


def get_chat_service(db: Annotated[Session, Depends(get_db)]) -> ChatService:
    return ChatService(db)


def build_preview(chat: ChatModel) -> ChatPreview:
    sorted_items = sorted(chat.items, key=lambda item: item.created_at)
    last_material_formula = next(
        (item.content for item in reversed(sorted_items) if item.type == "user_message"),
        None,
    )
    last_verdict = None

    for item in reversed(sorted_items):
        if item.type != "critique_card":
            continue

        try:
            payload = json.loads(item.content)
        except json.JSONDecodeError:
            payload = {}
        last_verdict = payload.get("verdict")
        break

    return ChatPreview(
        id=chat.id,
        title=chat.title,
        status=chat.status,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        last_material_formula=last_material_formula,
        last_verdict=last_verdict,
    )


def build_chat_item(item: ChatItemModel) -> ChatItem:
    return ChatItem(
        id=item.id,
        chat_id=item.chat_id,
        type=item.type,
        content=item.content,
        created_at=item.created_at,
    )


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
    return [build_preview(chat) for chat in chats]


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
        items=[build_chat_item(item) for item in sorted(chat.items, key=lambda item: item.created_at)],
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


@router.delete("", response_model=ChatClearResponse)
def clear_chats(
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatClearResponse:
    deleted_count = service.clear_chats()
    return ChatClearResponse(deleted_count=deleted_count, status="cleared")
