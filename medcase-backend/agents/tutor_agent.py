from services.llm_service import llm_service

class TutorAgent:
    async def evaluate_answer(self, student_answer: str, case_context: dict):
        """
        Öğrencinin cevabını alır, vaka bilgisiyle birlikte LLM'e gönderir
        ve eğitsel bir geri bildirim üretir.
        """
        
        # 1. LLM'e gidecek Prompt'u hazırla
        # PDF'te belirtilen "carefully designed prompt" burasıdır.
        prompt = f"""
        Sen bir tıp fakültesi eğitmenisin. Aşağıdaki vakayı ve öğrencinin cevabını analiz et.
        
        VAKA BİLGİSİ:
        {case_context.get('narrative', 'Veri yok')}
        
        SORU:
        {case_context.get('question', 'Veri yok')}
        
        ÖĞRENCİNİN CEVABI:
        {student_answer}
        
        GÖREV:
        Öğrenciye nazik ve öğretici bir dille geri bildirim ver.
        Cevabı yanlışsa neden yanlış olduğunu açıkla ve ipuçları ver.
        Cevabı doğruysa neden doğru olduğunu pekiştir.
        Cevabı hemen söyleme, mantık yürütmesini sağla.
        """

        # 2. LLM Servisini çağır
        feedback = await llm_service.generate_response(prompt)

        return {
            "is_correct": None, # LLM belirleyecek (ileride JSON parse edilebilir)
            "feedback": feedback
        }

# Dışarıya tek bir instance açıyoruz
tutor_agent = TutorAgent()