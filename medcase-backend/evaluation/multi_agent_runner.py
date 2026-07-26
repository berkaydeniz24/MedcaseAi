# evaluation/multi_agent_runner.py
"""
System B — Multi-Agent (roadmap item 3).

This is NOT a re-implementation. It calls the REAL production agents
(MCQAgent, DialogueAgent, TutorAgent) exactly as the live app calls
them, unmodified, and only normalizes their outputs into the shared
SystemRunResult shape so they can be compared against
evaluation/single_agent.py's monolithic output.

Mapping (mirrors how the production app actually uses these agents):
  1. MCQAgent.generate_mcq(case)              -> question, options, correct_index
  2. DialogueAgent.generate_response(mode="hint")   -> hint
  3. TutorAgent.run(mode="explain", over the MCQ from step 1) -> explanation

Case Selector Agent is not re-invoked here: the experiment harness supplies
the same case to both arms so the comparison isn't confounded by two
systems seeing different cases.
"""
import time
from contextlib import contextmanager
from typing import Dict, Optional

from dialogue.dialogue_agent import DialogueAgent
from mcq.mcq_agent import is_fallback_mcq, mcq_agent
from tutor.schemas import CaseContext, StepContext, TutorInput, UserContext
from tutor.tutor_agent import TutorAgent

from .schemas import CallMetrics, GeneratedContent, SystemRunResult

# Same role a real student's first free-text message would play; held constant
# across all cases so hint quality differences come from the case, not the prompt.
GENERIC_HINT_PROMPT = "What should I consider first when evaluating this patient?"


class _CallRecorder:
    """Accumulates across every generate_content call made inside one `with`
    block — MCQAgent can now make up to 2 raw calls per generate_mcq()
    (initial + one repair attempt), and both must count toward that step's
    cost, not just whichever call happened to run last."""
    def __init__(self):
        self.latency_ms = 0.0
        self.input_tokens = 0
        self.output_tokens = 0
        self.call_count = 0
        self.error = None


@contextmanager
def _record(client):
    """Non-invasively times a production agent's real generate_content call(s)
    and captures usage_metadata, without changing the agent's own code or
    return value. Patches client.models.generate_content for the duration of
    the `with` block only, then restores it."""
    rec = _CallRecorder()
    if client is None:
        rec.error = "client not initialized"
        yield rec
        return

    original = client.models.generate_content

    def wrapped(*args, **kwargs):
        start = time.perf_counter()
        try:
            resp = original(*args, **kwargs)
            usage = getattr(resp, "usage_metadata", None)
            if usage:
                rec.input_tokens += usage.prompt_token_count or 0
                rec.output_tokens += usage.candidates_token_count or 0
            rec.call_count += 1
            return resp
        except Exception as e:
            rec.error = str(e)
            raise
        finally:
            rec.latency_ms += (time.perf_counter() - start) * 1000

    client.models.generate_content = wrapped
    try:
        yield rec
    finally:
        client.models.generate_content = original


def _to_metrics(step: str, model: str, rec: _CallRecorder, ok: bool) -> CallMetrics:
    return CallMetrics(
        step=step, model=model, latency_ms=rec.latency_ms,
        input_tokens=rec.input_tokens or None,
        output_tokens=rec.output_tokens or None,
        success=ok and rec.error is None,
        error=rec.error,
    )


class MultiAgentRunner:
    def __init__(self):
        self.dialogue_agent = DialogueAgent()
        self.tutor_agent = TutorAgent()

    def run(self, case: Dict) -> SystemRunResult:
        calls = []
        question: Optional[str] = None
        options: Optional[list] = None
        correct_index: Optional[int] = None
        hint_text: Optional[str] = None
        explanation_text: Optional[str] = None

        # 1) MCQ Agent
        mcq = {}
        with _record(mcq_agent.client) as rec:
            try:
                mcq = mcq_agent.generate_mcq(case)
            except Exception as e:
                rec.error = rec.error or str(e)
        mcq_ok = bool(mcq.get("question")) and not is_fallback_mcq(mcq) and len(mcq.get("options", [])) == 4
        calls.append(_to_metrics("mcq", mcq_agent.model, rec, mcq_ok))
        if mcq_ok:
            question = mcq.get("question")
            options = mcq.get("options")
            correct_index = mcq.get("correctIndex")

        # 2) Dialogue Agent (hint mode) — independent of the MCQ, same as production
        with _record(self.dialogue_agent.client) as rec:
            hint_ok = False
            try:
                resp = self.dialogue_agent.generate_response(
                    user_input=GENERIC_HINT_PROMPT, case_data=case, mode="hint",
                )
                hint_text = resp.answer
                hint_ok = True
            except Exception as e:
                rec.error = rec.error or str(e)
        calls.append(_to_metrics("dialogue_hint", self.dialogue_agent.model_name, rec, hint_ok))

        # 3) Tutor Agent (explain mode, over the MCQ generated in step 1)
        if question and options and correct_index is not None:
            with _record(self.tutor_agent.client) as rec:
                explain_ok = False
                try:
                    tutor_inp = TutorInput(
                        case=CaseContext(
                            id=case["id"], title=case.get("title", ""),
                            summary=(case.get("narrative", "") or "")[:180],
                            narrative=case.get("narrative", ""),
                            step=StepContext(question=question, options=options, correct=correct_index),
                        ),
                        user=UserContext(selectedIndex=None, ask=""),
                        mode="explain",
                    )
                    tutor_out = self.tutor_agent.run(tutor_inp)
                    explanation_text = tutor_out.answer
                    explain_ok = True
                except Exception as e:
                    rec.error = rec.error or str(e)
            calls.append(_to_metrics("tutor_explain", self.tutor_agent.model_name, rec, explain_ok))
        else:
            calls.append(CallMetrics(
                step="tutor_explain", model=self.tutor_agent.model_name, latency_ms=0.0,
                success=False, error="skipped: no valid MCQ from step 1",
            ))

        content = None
        if question and options and correct_index is not None and hint_text and explanation_text:
            try:
                content = GeneratedContent(
                    question=question, options=options, correct_index=correct_index,
                    hint=hint_text, explanation=explanation_text,
                )
            except Exception:
                content = None

        return SystemRunResult(case_id=case["id"], system="multi_agent", content=content, calls=calls)


multi_agent_runner = MultiAgentRunner()
