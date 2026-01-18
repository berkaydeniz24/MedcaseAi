# src/tutor/schemas.py
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional, List, Dict, Any

Mode = Literal["hint", "explain", "teach"]
Lang = Literal["tr", "en"]

class StepContext(BaseModel):
    question: str = Field(min_length=1)
    options: List[str] = Field(min_length=2)
    correct: int = Field(ge=0)

    @field_validator("correct")
    @classmethod
    def correct_in_range(cls, v, info):
        opts = info.data.get("options") or []
        if opts and (v < 0 or v >= len(opts)):
            raise ValueError("correct index out of range")
        return v

class CaseContext(BaseModel):
    id: str = Field(min_length=1)
    title: str = ""
    summary: str = ""
    step: StepContext

class UserContext(BaseModel):
    selectedIndex: Optional[int] = Field(default=None, ge=0)
    ask: str = ""

    @field_validator("selectedIndex")
    @classmethod
    def selected_in_range(cls, v, info):
        # Range check is done in TutorAgent using step options length; keep minimal here
        return v

class TutorInput(BaseModel):
    case: CaseContext
    user: Optional[UserContext] = None
    mode: Mode = "explain"
    language: Lang = "tr"
    userLevel: str = "beginner"

class TutorOutput(BaseModel):
    answer: str
    followups: List[str]
    safety: Dict[str, Any]
    meta: Dict[str, Any]