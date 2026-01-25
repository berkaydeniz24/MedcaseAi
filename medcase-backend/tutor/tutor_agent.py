# tutor/tutor_agent.py
import os
import json
from dotenv import load_dotenv
from google import genai

from tutor.schemas import TutorInput, TutorOutput

load_dotenv()

class TutorAgent:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            self.client = None
        else:
            self.client = genai.Client(api_key=api_key)

        self.model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    def run(self, inp: TutorInput) -> TutorOutput:
        if not self.client:
            return self._error_response("GEMINI_API_KEY missing")

        # --- Pull core fields safely ---
        case_text = (inp.case.narrative or inp.case.summary or "").strip()
        step = inp.case.step
        user = inp.user

        # If MCQ step is missing, fallback to pure tutoring on narrative
        if step is None:
            prompt = self._build_narrative_only_prompt(inp, case_text)
            return self._call_llm(prompt)

        question = step.question
        options = step.options
        correct_index = step.correct

        selected_index = user.selectedIndex if user else None
        user_ask = (user.ask if user and user.ask else "").strip()

        # Validate selected index if present
        if selected_index is not None and (selected_index < 0 or selected_index >= len(options)):
            selected_index = None  # ignore invalid

        is_correct = (selected_index == correct_index) if selected_index is not None else None

        prompt = self._build_mcq_prompt(
            inp=inp,
            case_text=case_text,
            question=question,
            options=options,
            correct_index=correct_index,
            selected_index=selected_index,
            is_correct=is_correct,
            user_ask=user_ask
        )

        return self._call_llm(prompt)

    # -------- Prompt builders --------

    def _build_narrative_only_prompt(self, inp: TutorInput, case_text: str) -> str:
        return f"""
You are a medical education tutor. Educational use only. Not medical advice.

MODE: {inp.mode} (hint | explain | teach)
LANGUAGE: English only.

CASE NARRATIVE:
{case_text}

STUDENT MESSAGE:
{(inp.user.ask if inp.user else "Analyze this case.")}

RULES:
- Be educational and structured.
- Do not act like a clinician treating a real patient.
- Avoid giving direct orders.
""".strip()

    def _build_mcq_prompt(
        self,
        inp: TutorInput,
        case_text: str,
        question: str,
        options: list,
        correct_index: int,
        selected_index: int | None,
        is_correct: bool | None,
        user_ask: str
    ) -> str:
        # Format options
        opts_lines = "\n".join([f"{chr(65+i)}) {opt}" for i, opt in enumerate(options)])

        selected_line = "None"
        if selected_index is not None:
            selected_line = f"{chr(65+selected_index)}) {options[selected_index]}"

        correct_line = f"{chr(65+correct_index)}) {options[correct_index]}"

        # Strict behavior per mode
        # - hint: NEVER reveal correct option
        # - explain/teach: reveal dataset-correct option in final line
        mode = inp.mode

        return f"""
You are a medical education tutor (TutorAgent). Educational use only. Not medical advice.

LANGUAGE: English only.
MODE: {mode}

CASE NARRATIVE (use ONLY this as evidence):
{case_text}

MCQ QUESTION:
{question}

OPTIONS:
{opts_lines}

GROUND TRUTH (internal):
Correct: {correct_line}

STUDENT:
Selected: {selected_line}
Student message: {user_ask}

INSTRUCTIONS:
- If MODE=hint:
  - NEVER reveal which option is correct/incorrect.
  - Provide 2-3 hints based ONLY on the case narrative and option wording.
- If MODE=explain:
  - Provide a short rationale (3-6 bullets) why the correct option fits this case and why the chosen one is weaker (if chosen).
  - Final line MUST be: "Dataset-correct option: {correct_line}"
- If MODE=teach:
  - Provide a mini-lesson: (1) approach, (2) key clue, (3) common mistake.
  - Final line MUST be: "Dataset-correct option: {correct_line}"

IMPORTANT CONSTRAINT:
- Do NOT add external facts not supported by the case narrative.
- Do NOT cite general textbook knowledge beyond what is inferable from the narrative.
- Keep the response clear and student-friendly.

OUTPUT:
Return plain text only (no JSON).
""".strip()

    # -------- LLM call & output shaping --------

    def _call_llm(self, prompt: str) -> TutorOutput:
        try:
            resp = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            text = (resp.text or "").strip()

            return TutorOutput(
                answer=text if text else "No answer generated.",
                followups=["Want a hint or a deeper explanation?", "What made you choose that option?"],
                safety={"medical": "educational_only", "note": "Not medical advice."},
                meta={"model": self.model_name}
            )
        except Exception as e:
            return self._error_response(str(e))

    def _error_response(self, msg: str) -> TutorOutput:
        return TutorOutput(
            answer=f"Error: {msg}",
            followups=[],
            safety={"medical": "educational_only", "note": "Error"},
            meta={"error": True}
        )

# Singleton
tutor_agent = TutorAgent()
