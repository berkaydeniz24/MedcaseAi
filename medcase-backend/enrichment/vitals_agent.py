# enrichment/vitals_agent.py
"""
VitalsAgent — extracts explicitly-stated vital signs from a case narrative
(video-roadmap "vitals kartı"). Same response_schema + one-shot
repair-retry pattern as RubricAgent/MCQAgent. Unlike those, an EMPTY
result (no vitals mentioned at all) is a normal, valid outcome here, not
a failure — checked empirically before building this that only ~37% of
the 200 case narratives mention any vital sign.
"""
from __future__ import annotations

import logging
import os
from typing import Optional, Tuple

from services.gemini_client import GeminiClient
from services.prompt_loader import load_prompt

from .vitals_schemas import VitalsExtractionOutput

logger = logging.getLogger(__name__)

PROMPT_VERSION = "v1.0"


class VitalsAgent:
    def __init__(self):
        self.client = GeminiClient().client
        self.model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
        self._template = load_prompt("vitals_extraction", PROMPT_VERSION)

    def extract(self, case_id: str, narrative: str) -> VitalsExtractionOutput:
        prompt = self._template.substitute(case_id=case_id, narrative=narrative)

        result, raw_text, error = self._attempt(prompt, case_id, "initial")

        if result is None:
            repair_prompt = self._build_repair_prompt(prompt, raw_text, error)
            result, raw_text, error = self._attempt(repair_prompt, case_id, "repair")

        if result is None:
            raise RuntimeError(f"vitals_agent: extraction failed for case_id={case_id}: {error}")

        return result

    def _attempt(self, prompt: str, case_id: str, label: str) -> Tuple[Optional[VitalsExtractionOutput], Optional[str], Optional[str]]:
        try:
            logger.info("vitals_agent: %s attempt for case_id=%s prompt_version=%s", label, case_id, PROMPT_VERSION)
            resp = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": VitalsExtractionOutput,
                },
            )
            if resp.parsed is None:
                err = "response did not satisfy VitalsExtractionOutput validators"
                logger.warning("vitals_agent: %s attempt invalid for case_id=%s: %s | raw=%r",
                                label, case_id, err, (resp.text or "")[:500])
                return None, resp.text, err
            return resp.parsed, resp.text, None
        except Exception as e:
            logger.warning("vitals_agent: %s attempt failed for case_id=%s: %s", label, case_id, e)
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


vitals_agent = VitalsAgent()
