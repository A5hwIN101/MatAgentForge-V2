# backend/app/schemas/critique.py
from pydantic import BaseModel, Field
from typing import List, Optional

class Flag(BaseModel):
    icon: str
    text: str
    severity: str

class Suggestion(BaseModel):
    text: str
    rationale: str

class Citation(BaseModel):
    rule_id: str
    rule_name: str
    arxiv_id: str
    paper_title: str
    authors: str
    year: int | None = None
    url: str
    evidence_from_paper: str | None = None

class Contradiction(BaseModel):
    rule_a: str
    rule_b: str
    type: str
    resolution: str
    llm_reasoning: str

class CritiqueTrace(BaseModel):
    rules_matched: List[str] = Field(default_factory=list)
    contradictions: List[Contradiction] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)

class CritiqueCard(BaseModel):
    id: str
    material_formula: str
    verdict: str
    score: float
    domain_rules_passed: int
    domain_rules_total: int
    flags: List[Flag] = Field(default_factory=list)
    suggestions: List[Suggestion] = Field(default_factory=list)
    explanation: str
    trace: CritiqueTrace
