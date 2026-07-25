# mcq/schemas.py
"""
Strict output contract for MCQAgent. Where the old ad-hoc checks in
mcq_agent.py only verified that "question"/"options"/"correctIndex" keys
were present, this actually validates content: exactly 4 non-empty,
unique options, correctIndex in range, non-trivial question/rationale.
"""
from pydantic import BaseModel, Field, model_validator


class MCQOutput(BaseModel):
    question: str = Field(min_length=5)
    options: list[str] = Field(min_length=4, max_length=4)
    correctIndex: int = Field(ge=0, le=3)
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_options(self):
        cleaned = [option.strip() for option in self.options]
        if any(not option for option in cleaned):
            raise ValueError("MCQ options cannot be empty")
        if len({option.casefold() for option in cleaned}) != 4:
            raise ValueError("MCQ options must be unique")
        self.options = cleaned
        return self
