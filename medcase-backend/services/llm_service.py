import time

class LLMService:
    async def generate_response(self, prompt: str):
        # Gerçek API buraya bağlanacak
        print(f"🤖 LLM Prompt: {prompt[:50]}...")
        
        # Yapay bekleme
        time.sleep(1)
        
        return "Bu, Python backend'inden gelen örnek bir LLM cevabıdır."

llm_service = LLMService()