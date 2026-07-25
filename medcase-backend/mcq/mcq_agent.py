# mcq/mcq_agent.py
"""
MCQ Agent — generates one 4-option multiple-choice question from a case
narrative. Was previously services/mcq_generator.py; moved alongside
case_selector/, dialogue/, tutor/ so the folder layout matches how the
architecture is actually described (docs/architecture.md calls this the
"MCQ Agent").
"""
from __future__ import annotations

import logging
import os
import random
from typing import Any, Dict

from pydantic import ValidationError

from services.gemini_client import GeminiClient
from services.prompt_loader import load_prompt

from .schemas import MCQOutput

logger = logging.getLogger(__name__)

PROMPT_VERSION = "v1.0"


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

        prompt = self._template.substitute(
            case_id=case_id, specialty=specialty, difficulty=difficulty, narrative=narrative,
        )

        try:
            if self.client is None:
                raise RuntimeError("GEMINI_API_KEY missing — client not initialized")
            logger.info("mcq_agent: generating MCQ for case_id=%s prompt_version=%s", case_id, PROMPT_VERSION)
            resp = self.client.models.generate_content(model=self.model, contents=prompt)

            text = (resp.text or "").strip()
            text = text.replace("```json", "").replace("```", "").strip()

            # Strict contract: exactly 4 unique non-empty options, correctIndex
            # in range, non-trivial question/rationale — anything less raises
            # ValidationError and falls through to the fallback below, rather
            # than silently accepting malformed output (e.g. a clamped
            # out-of-range index).
            mcq = MCQOutput.model_validate_json(text)

            correct_answer_text = mcq.options[mcq.correctIndex]
            final_options = mcq.options.copy()
            random.shuffle(final_options)
            new_correct_index = final_options.index(correct_answer_text)

            return {
                "question": mcq.question,
                "options": final_options,
                "correctIndex": new_correct_index,
                "rationale": mcq.rationale,
            }

        except ValidationError as e:
            logger.error("mcq_agent: MCQ output failed schema validation for case_id=%s: %s", case_id, e)
        except Exception as e:
            logger.error("mcq_agent: MCQ generation failed for case_id=%s: %s", case_id, e)

        return {
            "question": "Vaka analizi sorusu yüklenirken bir hata oluştu.",
            "options": ["Seçenek A", "Seçenek B", "Seçenek C", "Seçenek D"],
            "correctIndex": 0,
            "rationale": "Sistem hatası.",
        }


mcq_agent = MCQAgent()
