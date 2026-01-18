# tutor/tutor_agent.py
import os
from dotenv import load_dotenv
from google import genai
# Senin orijinal şemalarını import ediyoruz
from .schemas import TutorInput, TutorOutput 

load_dotenv()

class TutorAgent:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            print("⚠️ HATA: GEMINI_API_KEY bulunamadı!")
            self.client = None
        else:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"Client init error: {e}")
                self.client = None
        
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    def run(self, inp: TutorInput) -> TutorOutput:
        """
        Girdi olarak senin tanımladığın 'TutorInput' nesnesini alır.
        """
        if not self.client:
            return self._error_response("API Key eksik.")

        try:
            case_text = inp.case.narrative if inp.case.narrative else inp.case.summary
            user_msg = inp.user.ask if inp.user and inp.user.ask else "Analyze this case."

            # --- YENİ İNGİLİZCE PROMPT ---
            system_instruction = f"""
            You are an expert medical tutor and clinician. 
            Current Mode: {inp.mode} (hint | explain | teach).
            Student Level: {inp.userLevel}.

            CASE CONTEXT:
            {case_text}

            STUDENT QUESTION:
            {user_msg}

            INSTRUCTIONS:
            1. LANGUAGE: You must ALWAYS respond in ENGLISH. Do not use any other language.
            2. PEDAGOGY: 
               - If mode is 'hint', guide the student SOCRATICALLY. Do not give the answer.
               - If mode is 'explain', provide distinct medical reasoning.
               - If mode is 'teach', act like a professor giving a lecture.
            3. TONE: Professional, encouraging, and academic.
            
            Provide your response now.
            """
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=system_instruction
            )
            
            answer_text = response.text if response.text else "Cevap üretilemedi."

            return TutorOutput(
                answer=answer_text,
                followups=["Detaylandırayım mı?", "Başka soru?"],
                safety={"medical": "educational_only", "note": "Not medical advice."},
                meta={"model": self.model_name}
            )

        except Exception as e:
            return self._error_response(str(e))

    def _error_response(self, msg: str) -> TutorOutput:
        return TutorOutput(
            answer=f"Hata oluştu: {msg}",
            followups=[],
            safety={"note": "Error"},
            meta={"error": True}
        )

tutor_agent = TutorAgent()