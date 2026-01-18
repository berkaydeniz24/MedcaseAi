# dialogue/dialogue_agent.py
import os
import json
from .gemini_client import get_gemini_client
from .prompts import DIALOGUE_SYSTEM_PROMPT
from .schemas import DialogueResponse

class DialogueAgent:
    def __init__(self):
        # --- HATA BURADAYDI: client tanımlanmamıştı ---
        try:
            self.client = get_gemini_client()
        except Exception as e:
            print(f"⚠️ DialogueAgent Başlatma Hatası: {e}")
            self.client = None
        # ---------------------------------------------
        
        self.model_id = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    def generate_response(self, user_input: str, case_data: dict, mode: str = "hint"):
        # Eğer client oluşmadıysa hata ver
        if not hasattr(self, 'client') or self.client is None:
            raise ValueError("DialogueAgent: Gemini Client başlatılamadı. API Key kontrolü yapın.")

        # case_data bazen Pydantic modeli değil dict gelebilir, güvenli hale getirelim
        try:
            case_str = json.dumps(case_data)
        except:
            case_str = str(case_data)

        prompt = f"{DIALOGUE_SYSTEM_PROMPT}\n\nCASE DATA: {case_str}\nMODE: {mode}\nUSER: {user_input}"
        
        try:
            # Yeni SDK formatı
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    'response_mime_type': 'application/json',
                    'response_schema': DialogueResponse,
                }
            )
            return response.parsed
        except Exception as e:
            raise RuntimeError(f"Gemini Cevap Üretme Hatası: {str(e)}")
    
    @property
    def model_name(self):
        return self.model_id