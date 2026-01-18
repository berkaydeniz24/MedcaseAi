# case_selector/schemas.py
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any

class CaseRubric(BaseModel):
    chief_complaint: str = ""
    red_flags: List[str] = []
    ddx_top: List[str] = []
    tests_initial: List[str] = []
    management_initial: List[str] = []
    pitfalls: List[str] = []

class CaseOutput(BaseModel):
    id: str
    title: str
    specialty: str = "Genel"
    difficulty: str = "Orta"
    narrative: str
    image: Optional[str] = None
    rubric: CaseRubric = Field(default_factory=CaseRubric)
    seed_questions: List[str] = []