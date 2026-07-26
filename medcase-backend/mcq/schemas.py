# mcq/schemas.py
"""
Strict output contract for MCQAgent, enforced via Gemini's response_schema
(not just post-hoc validation of free-text JSON) — see mcq/mcq_agent.py.
Structural correctness (4 unique option ids, no empty/duplicate option text,
a real correct_option_id, a non-trivial rationale) is guaranteed by
construction rather than hoped for from prompt wording alone.
"""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

OptionId = Literal["A", "B", "C", "D"]

# A handful of degenerate rationales seen in practice — reject them outright
# rather than trying to detect "superficiality" in general (that's a job for
# the LLM-as-a-Judge layer, not a Pydantic validator).
_TRIVIAL_RATIONALES = {
    "because it is correct",
    "this is correct",
    "this option is correct",
    "it is the correct answer",
}


class MCQOption(BaseModel):
    id: OptionId
    text: str = Field(min_length=1)


class DistractorExplanation(BaseModel):
    option_id: OptionId
    explanation: str = Field(min_length=1)


class MCQOutput(BaseModel):
    question: str = Field(min_length=10)
    options: List[MCQOption] = Field(min_length=4, max_length=4)
    correct_option_id: OptionId
    rationale: str = Field(min_length=20)
    # Fixed-shape list, not Dict[str, str] — Gemini's response_schema rejects
    # open/free-form object maps (errors on the implicit "additionalProperties").
    distractor_explanations: Optional[List[DistractorExplanation]] = None

    @model_validator(mode="after")
    def validate_options(self):
        ids = [opt.id for opt in self.options]
        if set(ids) != {"A", "B", "C", "D"}:
            raise ValueError("options must have exactly one each of A, B, C, D")

        cleaned = []
        for opt in self.options:
            text = opt.text.strip()
            if not text:
                raise ValueError(f"option {opt.id} text cannot be empty")
            cleaned.append((opt.id, text))
        self.options = [MCQOption(id=oid, text=text) for oid, text in cleaned]

        if len({text.casefold() for _, text in cleaned}) != 4:
            raise ValueError("option texts must be unique")

        if self.correct_option_id not in ids:
            raise ValueError("correct_option_id must reference one of the given options")

        if self.rationale.strip().casefold() in _TRIVIAL_RATIONALES:
            raise ValueError("rationale must not be a superficial placeholder")

        return self

    def option_text(self, option_id: str) -> str:
        return next(opt.text for opt in self.options if opt.id == option_id)
