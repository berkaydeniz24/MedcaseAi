# services/mcq_generator.py
from __future__ import annotations

import json
import os
import hashlib
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
from google import genai

load_dotenv()


def _stable_seed(case_id: str) -> str:
    # Case başına tutarlı üretim için (aynı case -> benzer çıktı)
    return hashlib.sha256(case_id.encode("utf-8")).hexdigest()[:12]


class MCQGenerator:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        self.client = genai.Client(api_key=api_key)
        self.model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    def generate_mcq(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns:
        {
          "question": str,
          "options": [str, str, str, str],
          "correctIndex": int,
          "rationale": str
        }
        """
        case_id = case.get("id", "unknown")
        narrative = case.get("narrative", "")
        specialty = case.get("specialty", "General")
        difficulty = case.get("difficulty", "Medium")

        seed = _stable_seed(case_id)

        system = f"""
You are generating ONE assessment-quality multiple-choice question (MCQ) for medical education.
This is educational only. Do not give real medical advice.

Constraints:
- Use ONLY the provided case narrative. Do not add external facts.
- Output MUST be valid JSON with fields:
  question (string), options (array of 4 or 5 strings), correctIndex (integer), rationale (string).
- correctIndex must be in range [0..len(options)-1].
- Options must be plausible and clearly distinguishable.
- Keep rationale short (2-5 sentences).
- LANGUAGE: English only.
- Make the MCQ aligned with the case specialty and difficulty.

Stability hint:
- Use this stable seed to keep output consistent: {seed}
""".strip()

        user = f"""
CASE_ID: {case_id}
SPECIALTY: {specialty}
DIFFICULTY: {difficulty}

NARRATIVE:
{narrative}
""".strip()

        resp = self.client.models.generate_content(
            model=self.model,
            contents=system + "\n\n" + user
        )

        text = (resp.text or "").strip()
        # Gemini bazen ```json ... ``` döndürür, temizleyelim
        text = text.replace("```json", "").replace("```", "").strip()

        data = json.loads(text)

        # Minimal validation
        if "question" not in data or "options" not in data or "correctIndex" not in data:
            raise ValueError("MCQ JSON missing required fields")
        if not isinstance(data["options"], list) or len(data["options"]) < 4:
            raise ValueError("MCQ options must be a list with 4+ items")
        if not (0 <= int(data["correctIndex"]) < len(data["options"])):
            raise ValueError("MCQ correctIndex out of range")

        # Normalize
        return {
            "question": str(data["question"]).strip(),
            "options": [str(x).strip() for x in data["options"]],
            "correctIndex": int(data["correctIndex"]),
            "rationale": str(data.get("rationale", "")).strip(),
        }


mcq_generator = MCQGenerator()
