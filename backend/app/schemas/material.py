# backend/app/schemas/material.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class Material(BaseModel):
    id: str
    formula: str
    normalized_formula: Optional[str] = None
    created_at: datetime

class MaterialScreening(BaseModel):
    material_id: str
    material_formula: str
    user_input: str
