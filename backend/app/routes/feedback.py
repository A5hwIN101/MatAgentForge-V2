from datetime import datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Critique, Feedback
from app.schemas.feedback import FeedbackRequest, FeedbackResponse

router = APIRouter(prefix="/api/critiques", tags=["feedback"])

VALID_ACTIONS = {"approve", "reject", "modify"}


@router.post("/{critique_id}/feedback", response_model=FeedbackResponse)
def save_feedback(
    critique_id: str,
    payload: FeedbackRequest,
    db: Annotated[Session, Depends(get_db)],
) -> FeedbackResponse:
    if payload.action not in VALID_ACTIONS:
        raise HTTPException(status_code=400, detail="Invalid action. Must be approve, reject, or modify.")

    critique = db.get(Critique, critique_id)
    if critique is None:
        raise HTTPException(status_code=400, detail="Critique not found.")

    feedback = Feedback(
        id=f"fb_{uuid4()}",
        critique_id=critique_id,
        action=payload.action,
        reason_text=payload.reason_text,
        created_at=datetime.utcnow(),
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    return FeedbackResponse(id=feedback.id, status="saved", action=feedback.action)
