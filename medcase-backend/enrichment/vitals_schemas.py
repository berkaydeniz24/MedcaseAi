# enrichment/vitals_schemas.py
"""
Strict output contract for VitalsAgent (enrichment/vitals_agent.py),
enforced via Gemini's response_schema — same pattern as
enrichment/schemas.py::RubricEnrichmentOutput. Unlike the rubric fields,
vitals are a pure extraction task: only what's explicitly stated in the
narrative as a number, never inferred or estimated. Coverage is real and
sparse (checked empirically before building this: only ~37% of the 200
narratives mention any vital sign at all) — every field here is Optional
on purpose, and the agent is instructed to leave a field null rather than
guess a "typical" value.
"""
from typing import Optional

from pydantic import BaseModel


class VitalReading(BaseModel):
    # Display-ready string with its unit, e.g. "38.9°C", "118 bpm",
    # "92/60 mmHg", "24/min", "89%" — exactly as stated in the narrative,
    # not converted or rounded.
    value: str
    is_abnormal: bool


class VitalsExtractionOutput(BaseModel):
    temperature: Optional[VitalReading] = None
    heart_rate: Optional[VitalReading] = None
    blood_pressure: Optional[VitalReading] = None
    respiratory_rate: Optional[VitalReading] = None
    spo2: Optional[VitalReading] = None
