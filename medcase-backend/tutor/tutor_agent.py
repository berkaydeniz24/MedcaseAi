# tutor/tutor_agent.py
import logging
import os

from services.gemini_client import GeminiClient
from services.prompt_loader import load_prompt
from tutor.schemas import TutorInput, TutorOutput

logger = logging.getLogger(__name__)

PROMPT_VERSION = "v1.0"


class TutorAgent:
    def __init__(self):
        try:
            self.client = GeminiClient().client
        except Exception as e:
            logger.warning("TutorAgent: client init failed: %s", e)
            self.client = None

        self.model_name = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
        self._mcq_template = load_prompt("tutor_mcq", PROMPT_VERSION)
        self._narrative_template = load_prompt("tutor_narrative", PROMPT_VERSION)

    def run(self, inp: TutorInput) -> TutorOutput:
        if not self.client:
            return self._error_response("GEMINI_API_KEY missing")

        case_text = (inp.case.narrative or inp.case.summary or "").strip()
        step = inp.case.step
        user = inp.user

        if step is None:
            prompt = self._build_narrative_only_prompt(inp, case_text)
            return self._call_llm(prompt)

        question = step.question
        options = step.options
        correct_index = step.correct

        selected_index = user.selectedIndex if user else None
        user_ask = (user.ask if user and user.ask else "").strip()

        if selected_index is not None and (selected_index < 0 or selected_index >= len(options)):
            selected_index = None

        prompt = self._build_mcq_prompt(
            inp=inp,
            case_text=case_text,
            question=question,
            options=options,
            correct_index=correct_index,
            selected_index=selected_index,
            user_ask=user_ask,
        )

        return self._call_llm(prompt)

    # -------- Prompt builders --------

    def _build_narrative_only_prompt(self, inp: TutorInput, case_text: str) -> str:
        return self._narrative_template.substitute(
            mode=inp.mode,
            case_text=case_text,
            user_ask=(inp.user.ask if inp.user else "Analyze this case."),
        )

    def _build_mcq_prompt(
        self,
        inp: TutorInput,
        case_text: str,
        question: str,
        options: list,
        correct_index: int,
        selected_index: "int | None",
        user_ask: str,
    ) -> str:
        opts_lines = "\n".join([f"{chr(65+i)}) {opt}" for i, opt in enumerate(options)])

        selected_line = "None"
        if selected_index is not None:
            selected_line = f"{chr(65+selected_index)}) {options[selected_index]}"

        correct_line = f"{chr(65+correct_index)}) {options[correct_index]}"

        return self._mcq_template.substitute(
            mode=inp.mode,
            case_text=case_text,
            question=question,
            options_block=opts_lines,
            correct_line=correct_line,
            selected_line=selected_line,
            user_ask=user_ask,
        )

    # -------- LLM call & output shaping --------

    def _call_llm(self, prompt: str) -> TutorOutput:
        try:
            logger.info("tutor_agent: generating response prompt_version=%s", PROMPT_VERSION)
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
            logger.error("tutor_agent: generation failed: %s", e)
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
