import asyncio
from typing import Annotated
from uuid import uuid4

import groq
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Critique, Material
from app.graph.workflow import InvalidMaterialFormulaError, run_screening_workflow
from app.services.chat_service import ChatService
from app.streaming.sse import SSEEmitter

router = APIRouter(prefix="/api/chats", tags=["screen"])


class ScreenRequest(BaseModel):
    formula: str


def get_chat_service(db: Annotated[Session, Depends(get_db)]) -> ChatService:
    return ChatService(db)


def persist_critique(db: Session, formula: str, critique_payload: dict) -> None:
    existing_critique = db.get(Critique, critique_payload["id"])
    if existing_critique is not None:
        return

    material = Material(
        id=f"mat_{uuid4()}",
        formula=formula,
        normalized_formula=formula,
    )
    db.add(material)
    db.flush()

    critique = Critique(
        id=critique_payload["id"],
        material_id=material.id,
        verdict=str(critique_payload["verdict"]),
        score=float(critique_payload["score"]),
        flags=critique_payload.get("flags", []),
        suggestions=critique_payload.get("suggestions", []),
        explanation=critique_payload.get("explanation", ""),
        trace=critique_payload.get("trace", {}),
    )
    db.add(critique)
    db.commit()


@router.post("/{chat_id}/screen")
async def screen_material(
    chat_id: str,
    payload: ScreenRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> StreamingResponse:
    chat = service.get_chat(chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    service.touch_chat_for_material(chat_id, payload.formula)
    service.append_item(chat_id, "user_message", payload.formula)
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
                final_state = await run_screening_workflow(
                    chat_id=chat_id,
                    run_id=run_id,
                    material_formula=payload.formula,
                    emit_event=emit_event,
                )
                critique_card = final_state.get("critique_card")
                if critique_card is not None:
                    critique_payload = critique_card.model_dump(mode="json")
                    persist_critique(service.db, payload.formula, critique_payload)
                    service.append_item(chat_id, "critique_card", critique_payload)
                await emit_event("screen.completed", {"status": "completed"})
            except InvalidMaterialFormulaError as error:
                error_payload = {
                    "code": "invalid_formula",
                    "title": "Invalid material formula",
                    "error": str(error),
                    "hint": "Check capitalization and element symbols, e.g. LiCoO2.",
                }
                service.append_item(chat_id, "error_card", error_payload)
                await emit_event(
                    "screen.failed",
                    error_payload,
                )
            except (groq.APIError, groq.APITimeoutError, groq.APIConnectionError) as error:
                error_payload = {"error": str(error)}
                service.append_item(chat_id, "error_card", error_payload)
                await emit_event("screen.failed", error_payload)
            except Exception as error:
                error_payload = {"error": str(error)}
                service.append_item(chat_id, "error_card", error_payload)
                await emit_event("screen.failed", error_payload)
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
