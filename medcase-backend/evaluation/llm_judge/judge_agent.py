# evaluation/llm_judge/judge_agent.py
"""
LLM-as-a-Judge (docs/evaluation_plan.md §3.2). Scores one already-generated
item (question/options/hint/explanation) against its case narrative, blind
to which system produced it — the prompt is never told, and this module's
caller (run_judge.py) only ever passes it content, never a system label.

Same response_schema + one-shot repair-retry pattern as MCQAgent/RubricAgent.
This is a JUDGE, not a content generator: on failure it raises rather than
returning a placeholder score, since a silently-wrong score would corrupt
the aggregate comparison rather than just degrade one case's UX.
"""
from __future__ import annotations

import logging
import os
from typing import List, Optional, Tuple

from services.gemini_client import GeminiClient
from services.prompt_loader import load_prompt

from .schemas import JudgeScores

logger = logging.getLogger(__name__)

PROMPT_VERSION = "v1.0"


class LLMJudge:
    def __init__(self):
        self.client = GeminiClient().client
        self.model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
        self._template = load_prompt("llm_judge", PROMPT_VERSION)

    def score(
        self,
        specialty: str,
        narrative: str,
        question: str,
        options: List[str],
        correct_index: int,
        hint: str,
        explanation: str,
        case_id: str = "unknown",
    ) -> JudgeScores:
        options_block = "\n".join(f"{chr(65 + i)}) {opt}" for i, opt in enumerate(options))
        correct_option = f"{chr(65 + correct_index)}) {options[correct_index]}"

        prompt = self._template.substitute(
            specialty=specialty,
            narrative=narrative,
            question=question,
            options_block=options_block,
            correct_option=correct_option,
            hint=hint,
            explanation=explanation,
        )

        result, raw_text, error = self._attempt(prompt, case_id, "initial")

        if result is None:
            repair_prompt = self._build_repair_prompt(prompt, raw_text, error)
            result, raw_text, error = self._attempt(repair_prompt, case_id, "repair")

        if result is None:
            raise RuntimeError(f"llm_judge: scoring failed for case_id={case_id}: {error}")

        return result

    def _attempt(self, prompt: str, case_id: str, label: str) -> Tuple[Optional[JudgeScores], Optional[str], Optional[str]]:
        try:
            logger.info("llm_judge: %s attempt for case_id=%s prompt_version=%s", label, case_id, PROMPT_VERSION)
            resp = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": JudgeScores,
                },
            )
            if resp.parsed is None:
                err = "response did not satisfy JudgeScores validators"
                logger.warning("llm_judge: %s attempt invalid for case_id=%s: %s | raw=%r",
                                label, case_id, err, (resp.text or "")[:500])
                return None, resp.text, err
            return resp.parsed, resp.text, None
        except Exception as e:
            logger.warning("llm_judge: %s attempt failed for case_id=%s: %s", label, case_id, e)
            return None, None, str(e)

    def _build_repair_prompt(self, original_prompt: str, raw_text: Optional[str], error: Optional[str]) -> str:
        return (
            f"{original_prompt}\n\n"
            f"--- REPAIR NEEDED ---\n"
            f"Your previous response was invalid: {error}\n"
            f"Previous response:\n{raw_text or '(no response text)'}\n\n"
            f"Provide a corrected response that fixes this specific problem while "
            f"still following the schema and all constraints above."
        )


llm_judge = LLMJudge()
