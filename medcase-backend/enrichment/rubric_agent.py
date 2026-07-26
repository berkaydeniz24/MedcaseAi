# enrichment/rubric_agent.py
"""
RubricAgent — fills the Case rubric (chief_complaint, red_flags, ddx_top,
tests_initial, management_initial, pitfalls), seed_questions, and a
re-assessed difficulty for a single case, grounded in its narrative.

Same response_schema + one-shot repair-retry pattern as mcq/mcq_agent.py.
Unlike MCQAgent, there is no safe placeholder fallback here — this agent is
used offline (enrichment/run_pilot.py), never on a live student request, so
on failure it raises instead of silently returning empty content.
"""
from __future__ import annotations

import logging
import os
from typing import Optional, Tuple

from services.gemini_client import GeminiClient
from services.prompt_loader import load_prompt

from .schemas import RubricEnrichmentOutput

logger = logging.getLogger(__name__)

PROMPT_VERSION = "v1.0"


class RubricAgent:
    def __init__(self):
        self.client = GeminiClient().client
        self.model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
        self._template = load_prompt("rubric_enrichment", PROMPT_VERSION)

    def enrich(self, case_id: str, specialty: str, narrative: str) -> RubricEnrichmentOutput:
        prompt = self._template.substitute(
            case_id=case_id, specialty=specialty, narrative=narrative,
        )

        result, raw_text, error = self._attempt(prompt, case_id, "initial")

        if result is None:
            repair_prompt = self._build_repair_prompt(prompt, raw_text, error)
            result, raw_text, error = self._attempt(repair_prompt, case_id, "repair")

        if result is None:
            raise RuntimeError(f"rubric_agent: enrichment failed for case_id={case_id}: {error}")

        return result

    def _attempt(self, prompt: str, case_id: str, label: str) -> Tuple[Optional[RubricEnrichmentOutput], Optional[str], Optional[str]]:
        try:
            logger.info("rubric_agent: %s attempt for case_id=%s prompt_version=%s", label, case_id, PROMPT_VERSION)
            resp = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": RubricEnrichmentOutput,
                },
            )
            if resp.parsed is None:
                err = "response did not satisfy RubricEnrichmentOutput validators"
                logger.warning("rubric_agent: %s attempt invalid for case_id=%s: %s | raw=%r",
                                label, case_id, err, (resp.text or "")[:500])
                return None, resp.text, err
            return resp.parsed, resp.text, None
        except Exception as e:
            logger.warning("rubric_agent: %s attempt failed for case_id=%s: %s", label, case_id, e)
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


rubric_agent = RubricAgent()
