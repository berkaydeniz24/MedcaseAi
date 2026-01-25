# dialogue/schemas.py

from pydantic import BaseModel
from typing import List, Literal

class SafetyInfo(BaseModel):
    medical: str = "educational_only"
    note: str

class MetaInfo(BaseModel):
    mode: Literal["hint", "explain", "teach"]
    specialty: str

class DialogueResponse(BaseModel):
    answer: str
    followups: List[str]
    safety: SafetyInfo
    meta: MetaInfo
