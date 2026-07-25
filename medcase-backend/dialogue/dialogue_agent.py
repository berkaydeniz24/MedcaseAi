# dialogue/dialogue_agent.py
import os
import json
from .gemini_client import get_gemini_client
from .prompts import DIALOGUE_SYSTEM_PROMPT
from .schemas import DialogueResponse

class DialogueAgent:
    def __init__(self):
        # Client init (safe)
        try:
            self.client = get_gemini_client()
        except Exception as e:
            print(f"⚠️ DialogueAgent Başlatma Hatası: {e}")
            self.client = None

        # Model id
        self.model_id = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

    def generate_response(
        self,
        user_input: str,
        case_data: dict,
        mode: str = "hint",
        language: str = "tr",
        user_level: str = "beginner",
        chat_history: list = None # 👈 YENİ: Geçmişi parametre olarak alıyoruz
    ):
        # Eğer client oluşmadıysa hata ver
        if not hasattr(self, "client") or self.client is None:
            raise ValueError("DialogueAgent: Gemini Client başlatılamadı. API Key kontrolü yapın.")

        # Mode guard
        if mode not in ["hint", "explain", "teach"]:
            mode = "hint"

        # Language guard
        if language not in ["tr", "en"]:
            language = "tr"

        # case_data güvenli stringify
        try:
            case_str = json.dumps(case_data, ensure_ascii=False)
        except Exception:
            case_str = str(case_data)

        # 1. GEÇMİŞ SOHBETİ HAZIRLA
        # Bu kısım sayesinde model önceki konuşmaları hatırlar ama sessionlar karışmaz.
        history_text = ""
        if chat_history:
            history_text = "\n--- PREVIOUS CHAT HISTORY ---\n"
            for msg in chat_history:
                # msg bir dict gelmeli: {'role': 'user'/'ai', 'content': '...'}
                role_label = "USER" if msg.get("role") == "user" else "AI MENTOR"
                content = msg.get("content", "")
                history_text += f"{role_label}: {content}\n"
            history_text += "--- END OF HISTORY ---\n"

        # 2. PROMPT'U BİRLEŞTİR
        # System Prompt + Case Data + History + Current Input
        prompt = (
            f"{DIALOGUE_SYSTEM_PROMPT}\n\n"
            f"LANGUAGE: {language}\n"
            f"USER_LEVEL: {user_level}\n"
            f"MODE: {mode}\n\n"
            f"CASE DATA: {case_str}\n\n"
            f"{history_text}\n"  # 👈 Geçmişi buraya gömdük
            f"USER (Current Input): {user_input}\n"
        )

        try:
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
            # Hata detayını görmek için print
            print(f"Gemini Hata Detayı: {e}")
            raise RuntimeError(f"Gemini Cevap Üretme Hatası: {str(e)}")

    @property
    def model_name(self):
        return self.model_id