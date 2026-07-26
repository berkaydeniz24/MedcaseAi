# mcq/mcq_agent.py
"""
MCQ Agent — generates one 4-option multiple-choice question from a case
narrative. Was previously services/mcq_generator.py; moved alongside
case_selector/, dialogue/, tutor/ so the folder layout matches how the
architecture is actually described (docs/architecture.md calls this the
"MCQ Agent").

Output is enforced via Gemini's response_schema (mcq/schemas.py::MCQOutput),
not just validated after the fact against free-text JSON. This is a
structural guarantee — a missing rationale, a duplicate option, a
correct_option_id that doesn't match any option, etc. cannot pass, whereas
prompt wording alone can only make those less likely. On schema failure we
give the model exactly one repair attempt (shown its own invalid output and
the validation error) before falling back to a placeholder MCQ.
"""
from __future__ import annotations

import json
import logging
import os
import random
from typing import Any, Dict, Optional, Tuple

from services.gemini_client import GeminiClient
from services.prompt_loader import load_prompt

from .schemas import MCQOutput

logger = logging.getLogger(__name__)

PROMPT_VERSION = "v1.1"

_FALLBACK = {
    "question": "Vaka analizi sorusu yüklenirken bir hata oluştu.",
    "options": ["Seçenek A", "Seçenek B", "Seçenek C", "Seçenek D"],
    "correctIndex": 0,
    "rationale": "Sistem hatası.",
}


def is_fallback_mcq(mcq: Dict[str, Any]) -> bool:
    """
    True if `mcq` is the placeholder returned on total generation failure.
    Callers that show MCQs to real students (routers/dialogue_router.py)
    MUST check this and refuse rather than silently letting a student
    "answer" a fake question — see docs/architecture.md §7 (P0 finding).
    Also used by evaluation/multi_agent_runner.py, which previously
    duplicated this exact literal comparison independently.
    """
    return mcq.get("options") == _FALLBACK["options"]


class MCQAgent:
    def __init__(self):
        try:
            self.client = GeminiClient().client
        except Exception as e:
            logger.warning("MCQAgent: client init failed: %s", e)
            self.client = None

        self.model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
        self._template = load_prompt("mcq", PROMPT_VERSION)

    def generate_mcq(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Vaka metninden 4 şıklı soru üretir.
        Şıkları karıştırarak doğru cevabın hep aynı şıkta olmasını engeller.
        """
        case_id = case.get("id", "unknown")
        narrative = case.get("narrative", "")
        specialty = case.get("specialty", "General")
        difficulty = case.get("difficulty", "Medium")

        if self.client is None:
            logger.error("mcq_agent: no client for case_id=%s (GEMINI_API_KEY missing)", case_id)
            return dict(_FALLBACK)

        prompt = self._template.substitute(
            case_id=case_id, specialty=specialty, difficulty=difficulty, narrative=narrative,
        )

        mcq, raw_text, error = self._attempt(prompt, case_id, "initial")

        if mcq is None:
            repair_prompt = self._build_repair_prompt(prompt, raw_text, error)
            mcq, raw_text, error = self._attempt(repair_prompt, case_id, "repair")

        if mcq is None:
            logger.error(json.dumps({
                "error_code": "MCQ_SCHEMA_VALIDATION_FAILED",
                "case_id": case_id,
                "attempts": 2,
            }))
            return dict(_FALLBACK)

        return self._shuffle_and_convert(mcq)

    # -------- generation attempts --------

    def _attempt(self, prompt: str, case_id: str, label: str) -> Tuple[Optional[MCQOutput], Optional[str], Optional[str]]:
        try:
            logger.info("mcq_agent: %s attempt for case_id=%s prompt_version=%s", label, case_id, PROMPT_VERSION)
            resp = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": MCQOutput,
                },
            )
            if resp.parsed is None:
                # Schema-shape-valid JSON that failed our custom validators
                # (or wasn't valid JSON at all) — resp.text still has it.
                err = "response did not satisfy MCQOutput validators"
                logger.warning("mcq_agent: %s attempt invalid for case_id=%s: %s | raw=%r",
                                label, case_id, err, (resp.text or "")[:500])
                return None, resp.text, err
            return resp.parsed, resp.text, None
        except Exception as e:
            logger.warning("mcq_agent: %s attempt failed for case_id=%s: %s", label, case_id, e)
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

    # -------- output shaping --------

    def _shuffle_and_convert(self, mcq: MCQOutput) -> Dict[str, Any]:
        correct_text = mcq.option_text(mcq.correct_option_id)
        final_options = [opt.text for opt in mcq.options]
        random.shuffle(final_options)
        new_correct_index = final_options.index(correct_text)

        return {
            "question": mcq.question,
            "options": final_options,
            "correctIndex": new_correct_index,
            "rationale": mcq.rationale,
        }


mcq_agent = MCQAgent()
