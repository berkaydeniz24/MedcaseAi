# src/tutor/tutor_agent.py
import os
import re
from .schemas import TutorInput, TutorOutput
from .prompts import tutor_system_prompt, tutor_user_prompt
from .gemini_client import GeminiClient

def _make_followups(language: str):
    if language == "tr":
        return [
            "Bu vakada ayırıcı tanıda hangi 2 olasılık daha düşünülmeli?",
            "Bu durumda ilk isteyeceğin ek tetkik ne olurdu?",
            "Hangi klinik bulgu kararını en çok etkiler?"
        ]
    return [
        "What are two key differentials here?",
        "What additional test would you order first?",
        "Which finding most strongly drives your decision?"
    ]

def _postprocess(raw: str | None, inp: TutorInput) -> str:
    txt = (raw or "").strip()
    if not txt:
        return "Yanıt üretilemedi." if inp.language == "tr" else "No answer generated."

    if inp.mode == "hint":
        txt = re.sub(r"(?i)\b(doğru\s*cevap|correct\s*answer)\b.*", "", txt).strip()
        if inp.language == "tr":
            txt = re.sub(r"(?m)^Final:.*$", "Final: Bu soruda doğru yaklaşımı bulman için ipuçları:", txt)
        else:
            txt = re.sub(r"(?m)^Final:.*$", "Final: Hints to help you choose the best option:", txt)

        txt = re.sub(r"(?m)^\s*[A-E]\)\s+.*$", "", txt).strip()
        if inp.language == "tr":
            txt = txt.replace("ilk yapılması gereken işlem değildir", "bu durumda öncelik sıralamasında daha geride kalabilir")
            txt = txt.replace("yanlıştır", "bu senaryoda en güçlü tercih olmayabilir")
            txt = txt.replace("doğrudur", "yüksek olasılıkla uygun yaklaşımdır")
        else:
            txt = txt.replace("is not the first step", "may not be the highest-priority first step")
            txt = txt.replace("is wrong", "may be less appropriate here")
            txt = txt.replace("is correct", "is likely appropriate here")
        txt = re.sub(r"\b[A-E]\)\s*", "", txt)

    # explain/teach: Final satırını dataset-correct ile standardize et
    if inp.mode in ("explain", "teach"):
        correct_idx = inp.case.step.correct
        correct_text = inp.case.step.options[correct_idx]
        final_line = (
            f"Final: Dataset’e göre doğru seçenek: {chr(65+correct_idx)}) {correct_text}."
            if inp.language == "tr"
            else f"Final: Dataset-correct option: {chr(65+correct_idx)}) {correct_text}."
        )
        # Final satırı yoksa ekle; varsa replace et
        if re.search(r"(?m)^Final:", txt):
            txt = re.sub(r"(?m)^Final:.*$", final_line, txt, count=1)
        else:
            txt = final_line + "\n\n" + txt

    return txt

class TutorAgent:
    def __init__(self):
        self.client = GeminiClient()
        self.model = os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash")

    def run(self, inp: TutorInput) -> TutorOutput:
        # selectedIndex range check (options length)
        if inp.user and inp.user.selectedIndex is not None:
            if inp.user.selectedIndex < 0 or inp.user.selectedIndex >= len(inp.case.step.options):
                inp.user.selectedIndex = None

        system = tutor_system_prompt(inp.language, inp.mode)
        user = tutor_user_prompt(inp.model_dump())

        raw = self.client.generate(system=system, user=user, model=self.model)
        answer = _postprocess(raw, inp)

        return TutorOutput(
            answer=answer,
            followups=_make_followups(inp.language),
            safety={
                "medical": "educational_only",
                "note": "Not medical advice. For emergencies seek professional care."
            },
            meta={"model": self.model, "mode": inp.mode, "caseId": inp.case.id},
        )