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

class VitalReading(BaseModel):
    value: str
    is_abnormal: bool

class CaseVitals(BaseModel):
    temperature: Optional[VitalReading] = None
    heart_rate: Optional[VitalReading] = None
    blood_pressure: Optional[VitalReading] = None
    respiratory_rate: Optional[VitalReading] = None
    spo2: Optional[VitalReading] = None

class CaseSource(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    doi: Optional[str] = None
    authors: Optional[str] = None
    year: Optional[int] = None
    license_name: Optional[str] = None
    license_url: Optional[str] = None
    citation_text: Optional[str] = None

class CaseOutput(BaseModel):
    id: str
    title: str
    specialty: str = "General"
    difficulty: str = "Intermediate"
    narrative: str
    image: Optional[str] = None
    rubric: CaseRubric = Field(default_factory=CaseRubric)
    seed_questions: List[str] = []
    source: Optional[CaseSource] = None
    vitals: CaseVitals = Field(default_factory=CaseVitals)