# services/mcq_generator.py
from __future__ import annotations

import json
import os
import random
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
from google import genai

load_dotenv()

class MCQGenerator:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        self.client = genai.Client(api_key=api_key)
        self.model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

    def generate_mcq(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Vaka metninden 4 şıklı soru üretir.
        Şıkları karıştırarak doğru cevabın hep aynı şıkta olmasını engeller.
        """
        case_id = case.get("id", "unknown")
        narrative = case.get("narrative", "")
        specialty = case.get("specialty", "General")
        difficulty = case.get("difficulty", "Medium")

        # System Prompt: Sadece geçerli bir JSON istiyoruz.
        # Sıralama talimatı vermiyoruz, çünkü Python tarafında biz karıştıracağız.
        system = """
You are generating ONE assessment-quality multiple-choice question (MCQ) for medical education.
This is educational only. Do not give real medical advice.

Constraints:
- Use ONLY the provided case narrative. Do not add external facts.
- Output MUST be valid JSON with fields:
  question (string), options (array of 4 strings), correctIndex (integer), rationale (string).
- correctIndex must point to the correct option in your list (0 to 3).
- Options must be plausible and clearly distinguishable.
- Keep rationale short (2-5 sentences).
- LANGUAGE: English only.
""".strip()

        user = f"""
CASE_ID: {case_id}
SPECIALTY: {specialty}
DIFFICULTY: {difficulty}

NARRATIVE:
{narrative}
""".strip()

        try:
            resp = self.client.models.generate_content(
                model=self.model,
                contents=system + "\n\n" + user
            )

            text = (resp.text or "").strip()
            # Markdown temizliği
            text = text.replace("```json", "").replace("```", "").strip()

            data = json.loads(text)

            # --- VALIDASYON ---
            if "question" not in data or "options" not in data or "correctIndex" not in data:
                raise ValueError("MCQ JSON missing required fields")
            
            # --- SAĞLAM KARIŞTIRMA (ROBUST SHUFFLE) ---
            orig_options = [str(x).strip() for x in data["options"]]
            orig_idx = int(data["correctIndex"])
            question = str(data["question"]).strip()
            rationale = str(data.get("rationale", "")).strip()

            # 1. Doğru cevabın metnini bul
            # Eğer LLM hatalı index verdiyse (liste dışı), mecburen 0. elemanı doğru say
            if 0 <= orig_idx < len(orig_options):
                correct_answer_text = orig_options[orig_idx]
            else:
                correct_answer_text = orig_options[0]

            # 2. Listeyi kopyala ve karıştır
            final_options = orig_options.copy()
            random.shuffle(final_options)

            # 3. Doğru cevabın YENİ indeksini bul
            new_correct_index = final_options.index(correct_answer_text)

            return {
                "question": question,
                "options": final_options,
                "correctIndex": new_correct_index, # Artık rastgele bir yer (0,1,2,3)
                "rationale": rationale,
            }

        except Exception as e:
            print(f"MCQ Generator Error: {e}")
            # Hata durumunda fallback (Yedek)
            return {
                "question": "Vaka analizi sorusu yüklenirken bir hata oluştu.",
                "options": ["Seçenek A", "Seçenek B", "Seçenek C", "Seçenek D"],
                "correctIndex": 0,
                "rationale": "Sistem hatası."
            }

mcq_generator = MCQGenerator()