# dialogue/dialogue_agent.py
import json
import logging
import os

from services.gemini_client import GeminiClient
from services.prompt_loader import load_prompt
from .schemas import DialogueResponse

logger = logging.getLogger(__name__)

PROMPT_VERSION = "v1.0"


class DialogueAgent:
    def __init__(self):
        try:
            self.client = GeminiClient().client
        except Exception as e:
            logger.warning("DialogueAgent: client init failed: %s", e)
            self.client = None

        self.model_id = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
        self._template = load_prompt("dialogue", PROMPT_VERSION)

    def generate_response(
        self,
        user_input: str,
        case_data: dict,
        mode: str = "hint",
        language: str = "tr",
        user_level: str = "beginner",
        chat_history: list = None,
    ):
        if not hasattr(self, "client") or self.client is None:
            raise ValueError("DialogueAgent: Gemini Client başlatılamadı. API Key kontrolü yapın.")

        if mode not in ["hint", "explain", "teach"]:
            mode = "hint"

        if language not in ["tr", "en"]:
            language = "tr"

        try:
            case_str = json.dumps(case_data, ensure_ascii=False)
        except Exception:
            case_str = str(case_data)

        history_text = ""
        if chat_history:
            history_text = "\n--- PREVIOUS CHAT HISTORY ---\n"
            for msg in chat_history:
                role_label = "USER" if msg.get("role") == "user" else "AI MENTOR"
                content = msg.get("content", "")
                history_text += f"{role_label}: {content}\n"
            history_text += "--- END OF HISTORY ---\n"

        prompt = self._template.substitute(
            language=language,
            user_level=user_level,
            mode=mode,
            case_data=case_str,
            history_text=history_text,
            user_input=user_input,
        )

        try:
            logger.info(
                "dialogue_agent: generating response case_id=%s mode=%s prompt_version=%s",
                case_data.get("id"), mode, PROMPT_VERSION,
            )
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": DialogueResponse,
                },
            )
            return response.parsed
        except Exception as e:
            logger.error("dialogue_agent: generation failed for case_id=%s: %s", case_data.get("id"), e)
            raise RuntimeError(f"Gemini Cevap Üretme Hatası: {str(e)}")

    @property
    def model_name(self):
        return self.model_id
