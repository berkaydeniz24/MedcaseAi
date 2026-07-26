# evaluation/llm_judge/schemas.py
"""
Output contract for the LLM-as-a-Judge layer (docs/evaluation_plan.md §3.2).
Deliberately mirrors the 5-criterion 1-5 rubric already used by the Human
Expert Evaluation form (evaluation/human_eval/) — same criteria, same
scale — so LLM-judge and human scores can be directly compared/correlated
later, not just eyeballed side by side.
"""
from typing import List

from pydantic import BaseModel, Field


class CriterionScore(BaseModel):
    score: int = Field(ge=1, le=5)
    justification: str = Field(min_length=10)


class JudgeScores(BaseModel):
    clinical_correctness: CriterionScore
    relevance: CriterionScore
    consistency: CriterionScore
    educational_usefulness: CriterionScore
    clarity: CriterionScore
    concerns: List[str] = Field(
        default_factory=list,
        description="Any hallucinated facts, unsupported claims, or unsafe "
                    "content noticed while judging. Empty list if none.",
    )
