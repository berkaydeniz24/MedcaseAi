# dialogue/gemini_client.py
import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("⚠️ HATA: GEMINI_API_KEY bulunamadı!")
        return None
    
    try:
        # Yeni SDK client yapısı
        client = genai.Client(api_key=api_key)
        return client
    except Exception as e:
        print(f"Client oluşturma hatası: {e}")
        return None