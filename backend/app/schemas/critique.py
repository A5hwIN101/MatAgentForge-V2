# backend/app/schemas/critique.py
from pydantic import BaseModel
from typing import Optional, List

class Flag(BaseModel):
    icon: str
    text: str
    severity: str

class Suggestion(BaseModel):
    text: str
    rationale: str

class Citation(BaseModel):
    rule_id: str
    source: str
    confidence: float

class Contradiction(BaseModel):
    rule_a: str
    rule_b: str
    type: str
    resolution: str
    llm_reasoning: str

class CritiqueTrace(BaseModel):
    rules_matched: List[str] = []
    contradictions: List[Contradiction] = []
    citations: List[Citation] = []

class CritiqueCard(BaseModel):
    id: str
    material_formula: str
    verdict: str
    score: float
    domain_rules_passed: int
    domain_rules_total: int
    flags: List[Flag] = []
    suggestions: List[Suggestion] = []
    explanation: str
    trace: CritiqueTrace
