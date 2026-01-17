from agents.case_selector import case_selector_agent
from agents.tutor_agent import tutor_agent # <-- Artık bu satır aktif!

class DialogueAgent:
    def start_simulation(self):
        # Yeni vaka başlat
        return case_selector_agent.select_case()

    async def handle_response(self, answer: str, case_data: dict):
        # Öğrenci cevap verdiğinde Tutor Agent devreye girer
        print("💬 DialogueAgent: Cevap Tutor Agent'a iletiliyor...")
        
        result = await tutor_agent.evaluate_answer(answer, case_data)
        
        return result

dialogue_agent = DialogueAgent()