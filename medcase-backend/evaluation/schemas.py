# evaluation/schemas.py
"""
Common output contract for the Single-Agent vs Multi-Agent experiment
(roadmap item 3). Both experimental arms (evaluation/single_agent.py and
evaluation/multi_agent_runner.py) must produce a SystemRunResult so that
downstream scoring (clinical correctness, MCQ quality, educational quality,
consistency, system performance) runs against one shape regardless of which
architecture produced it.
"""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

SystemType = Literal["single_agent", "multi_agent"]


class GeneratedContent(BaseModel):
    """
    The comparable content both systems must produce for one case.
    This is the unit that gets scored (Clinical Correctness, MCQ Quality,
    Educational Quality, Case Consistency) — NOT where performance data lives.
    """
    question: str
    options: List[str] = Field(min_length=4, max_length=4)
    correct_index: int = Field(ge=0, le=3)
    hint: str
    explanation: str


class CallMetrics(BaseModel):
    """
    One measured LLM call. A single-agent run should produce exactly one of
    these; a multi-agent run produces one per specialist agent invoked
    (mcq, dialogue_hint, tutor_explain, ...). This is the raw material for
    the 'System Performance' evaluation dimension (latency, token usage,
    API call count, failure rate).
    """
    step: str
    model: str
    latency_ms: float
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    success: bool
    error: Optional[str] = None


class AutomatedChecks(BaseModel):
    """
    Automated Evaluation layer (docs/evaluation_plan.md §3.1) — pure, code-only
    checks over a SystemRunResult's content. Intentionally coarse: catches
    gross structural problems (duplicate options, an answer leaking into the
    question/hint), not nuanced clinical/educational quality — that's what the
    LLM-as-a-Judge and Human Expert layers are for. See evaluation/automated_checks.py.
    """
    schema_valid: bool
    option_count_ok: bool
    has_empty_option: bool
    has_duplicate_options: bool
    correct_index_in_range: bool
    explanation_grounds_correct_option: Optional[bool] = None
    hint_leaks_correct_option: Optional[bool] = None
    answer_leaked_in_question: Optional[bool] = None
    flags: List[str] = Field(default_factory=list)


class SystemRunResult(BaseModel):
    """
    One system's full run against one case. Both experiment arms return
    this same shape for a given case_id, which is what makes the
    single-agent vs multi-agent comparison apples-to-apples.
    """
    case_id: str
    system: SystemType
    content: Optional[GeneratedContent] = None
    calls: List[CallMetrics] = Field(default_factory=list)

    @property
    def total_latency_ms(self) -> float:
        return sum(c.latency_ms for c in self.calls)

    @property
    def total_api_calls(self) -> int:
        return len(self.calls)

    @property
    def total_input_tokens(self) -> int:
        return sum(c.input_tokens or 0 for c in self.calls)

    @property
    def total_output_tokens(self) -> int:
        return sum(c.output_tokens or 0 for c in self.calls)

    @property
    def failed(self) -> bool:
        return self.content is None or any(not c.success for c in self.calls)

    def to_summary_dict(self) -> dict:
        """Flat dict for CSV/pandas — the shape evaluation/run_pilot.py writes out."""
        return {
            "case_id": self.case_id,
            "system": self.system,
            "failed": self.failed,
            "total_latency_ms": round(self.total_latency_ms, 1),
            "total_api_calls": self.total_api_calls,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "question": self.content.question if self.content else None,
            "options": self.content.options if self.content else None,
            "correct_index": self.content.correct_index if self.content else None,
            "hint": self.content.hint if self.content else None,
            "explanation": self.content.explanation if self.content else None,
        }
