# backend/app/schemas/feedback.py
from pydantic import BaseModel
from typing import Optional

class FeedbackRequest(BaseModel):
    critique_id: str
    action: str
    reason_text: Optional[str] = None

class FeedbackResponse(BaseModel):
    id: str
    status: str
