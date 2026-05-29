import asyncio
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
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
        yield SSEEmitter.build_event(
            event="screen.started",
            chat_id=chat_id,
            run_id=run_id,
            data={"formula": payload.formula},
        )
        await asyncio.sleep(1)

        yield SSEEmitter.build_event(
            event="step.started",
            chat_id=chat_id,
            run_id=run_id,
            data={"step": "load_domain_rules", "status": "started"},
        )
        await asyncio.sleep(1)
        yield SSEEmitter.build_event(
            event="step.updated",
            chat_id=chat_id,
            run_id=run_id,
            data={
                "step": "load_domain_rules",
                "label": "⚙ Loading domain rules...",
                "status": "in_progress",
            },
        )
        await asyncio.sleep(2)

        yield SSEEmitter.build_event(
            event="step.started",
            chat_id=chat_id,
            run_id=run_id,
            data={"step": "candidate_analysis", "status": "started"},
        )
        await asyncio.sleep(1)
        yield SSEEmitter.build_event(
            event="step.updated",
            chat_id=chat_id,
            run_id=run_id,
            data={
                "step": "candidate_analysis",
                "label": f"🔍 Screening {payload.formula}...",
                "status": "in_progress",
            },
        )
        await asyncio.sleep(2)

        yield SSEEmitter.build_event(
            event="step.started",
            chat_id=chat_id,
            run_id=run_id,
            data={"step": "critique_generation", "status": "started"},
        )
        await asyncio.sleep(1)
        yield SSEEmitter.build_event(
            event="step.updated",
            chat_id=chat_id,
            run_id=run_id,
            data={
                "step": "critique_generation",
                "label": "⚠ Running critique...",
                "status": "in_progress",
            },
        )
        await asyncio.sleep(2)

        explanation_words = (
            "LiCoO2 remains feasible but carries cobalt cost risk and thermal safety concerns."
        ).split()
        for word in explanation_words:
            yield SSEEmitter.build_event(
                event="text.delta",
                chat_id=chat_id,
                run_id=run_id,
                data={"delta": f"{word} "},
            )
            await asyncio.sleep(1)

        yield SSEEmitter.build_event(
            event="critique.ready",
            chat_id=chat_id,
            run_id=run_id,
            data={
                "id": f"crit_{uuid4()}",
                "material_formula": payload.formula,
                "verdict": "Feasible with concerns",
                "score": 7.2,
                "domain_rules_passed": 3,
                "domain_rules_total": 3,
                "flags": [
                    {
                        "icon": "⚠",
                        "text": "Co scarcity — cost risk at scale",
                        "severity": "warning",
                    },
                    {
                        "icon": "⚠",
                        "text": "Thermal runaway above 150°C",
                        "severity": "warning",
                    },
                    {
                        "icon": "✅",
                        "text": "Ionic conductivity — strong",
                        "severity": "success",
                    },
                ],
                "suggestions": [
                    {
                        "text": "Substitute Ni-Mn for Co (NMC path)",
                        "rationale": "Reduce cobalt dependency while preserving cathode performance.",
                    },
                    {
                        "text": "Add thermal management constraint",
                        "rationale": "Account for elevated temperature safety risks in screening.",
                    },
                ],
                "explanation": "LiCoO2 remains feasible but requires explicit handling of cost and thermal safety tradeoffs.",
                "trace": {
                    "rules_matched": [
                        "high_ionic_conductivity",
                        "cobalt_scarcity_penalty",
                        "thermal_runaway_guardrail",
                    ],
                    "contradictions": [],
                    "citations": [
                        {
                            "rule_id": "high_ionic_conductivity",
                            "source": "mock_materials_project_rulepack",
                            "confidence": 0.92,
                        }
                    ],
                },
            },
        )
        await asyncio.sleep(1)

        yield SSEEmitter.build_event(
            event="screen.completed",
            chat_id=chat_id,
            run_id=run_id,
            data={"status": "completed"},
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
