# backend/app/schemas/sse.py
from pydantic import BaseModel
from typing import Optional, Dict, Any

class StepEvent(BaseModel):
    step: str
    label: str
    status: str
    meta: Optional[Dict[str, Any]] = None

class SSEEvent(BaseModel):
    event: str
    chat_id: str
    run_id: str
    timestamp: str
    data: Dict[str, Any]
