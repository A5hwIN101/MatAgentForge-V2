import asyncio
from typing import Annotated
from uuid import uuid4

import groq
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.graph.workflow import run_screening_workflow
from app.services.chat_service import ChatService
from app.streaming.sse import SSEEmitter

router = APIRouter(prefix="/api/chats", tags=["screen"])


class ScreenRequest(BaseModel):
    formula: str


def get_chat_service(db: Annotated[Session, Depends(get_db)]) -> ChatService:
    return ChatService(db)


@router.post("/{chat_id}/screen")
async def screen_material(
    chat_id: str,
    payload: ScreenRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> StreamingResponse:
    chat = service.get_chat(chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    run_id = str(uuid4())

    async def event_stream():
        queue: asyncio.Queue[str | None] = asyncio.Queue()

        async def emit_event(event: str, data: dict) -> None:
            await queue.put(
                SSEEmitter.build_event(
                    event=event,
                    chat_id=chat_id,
                    run_id=run_id,
                    data=data,
                )
            )

        async def run_workflow() -> None:
            await emit_event("screen.started", {"formula": payload.formula})
            try:
                await run_screening_workflow(
                    chat_id=chat_id,
                    run_id=run_id,
                    material_formula=payload.formula,
                    emit_event=emit_event,
                )
                await emit_event("screen.completed", {"status": "completed"})
            except (groq.APIError, groq.APITimeoutError, groq.APIConnectionError) as error:
                await emit_event("screen.failed", {"error": str(error)})
            except Exception as error:
                await emit_event("screen.failed", {"error": str(error)})
            finally:
                await queue.put(None)

        workflow_task = asyncio.create_task(run_workflow())

        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item
        finally:
            await workflow_task

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
