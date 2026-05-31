from typing import Awaitable, Callable, List, TypedDict

from app.schemas.critique import CritiqueCard


EmitEvent = Callable[[str, dict], Awaitable[None]]


class ScreeningState(TypedDict, total=False):
    material_formula: str
    rules_loaded: List[dict]
    candidate: dict
    matched_rules: List[dict]
    violations: List[dict]
    contradictions: List[dict]
    explanation_stream: str
    critique_card: CritiqueCard
    critique_payload: dict
    chat_id: str
    run_id: str
    emit_event: EmitEvent
