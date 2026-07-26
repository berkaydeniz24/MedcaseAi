# enrichment/schemas.py
"""
Strict output contract for RubricAgent (enrichment/rubric_agent.py),
enforced via Gemini's response_schema — same pattern as mcq/schemas.py.
Fills the Case.rubric_json / seed_questions_json / difficulty fields that
have been empty/uniform since the dataset was seeded (see docs/dataset.md).
"""
from typing import List, Literal

from pydantic import BaseModel, Field, model_validator

Difficulty = Literal["Beginner", "Intermediate", "Advanced"]


class RubricEnrichmentOutput(BaseModel):
    chief_complaint: str = Field(min_length=3)
    red_flags: List[str] = Field(min_length=1, max_length=6)
    ddx_top: List[str] = Field(min_length=2, max_length=6)
    tests_initial: List[str] = Field(min_length=1, max_length=6)
    management_initial: List[str] = Field(min_length=1, max_length=6)
    pitfalls: List[str] = Field(min_length=1, max_length=6)
    seed_questions: List[str] = Field(min_length=3, max_length=5)
    difficulty: Difficulty
    difficulty_justification: str = Field(min_length=10)

    @model_validator(mode="after")
    def validate_nonempty_items(self):
        list_fields = [
            "red_flags", "ddx_top", "tests_initial",
            "management_initial", "pitfalls", "seed_questions",
        ]
        for field in list_fields:
            items = getattr(self, field)
            cleaned = [i.strip() for i in items if i.strip()]
            if not cleaned:
                raise ValueError(f"{field} must contain at least one non-empty item")
            setattr(self, field, cleaned)
        return self
