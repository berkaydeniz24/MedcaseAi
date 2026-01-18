# src/tutor/gemini_client.py
import os
import time
from google import genai
from google.genai import types

class GeminiClient:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        self.client = genai.Client(api_key=api_key)

    def generate(self, system: str, user: str, model: str, timeout_s: int = 25) -> str:
        # Basit exponential backoff: 429/503 gibi durumlarda yeniden dener
        last_err = None
        for attempt in range(4):
            try:
                resp = self.client.models.generate_content(
                    model=model,
                    contents=[
                        types.Content(role="user", parts=[types.Part(text=user)])
                    ],
                    config=types.GenerateContentConfig(
                        system_instruction=system,
                        temperature=0.4,
                        max_output_tokens=1200,
                    ),
                )
                return (resp.text or "").strip()
            except Exception as e:
                last_err = e
                msg = str(e)
                retriable = ("429" in msg) or ("RESOURCE_EXHAUSTED" in msg) or ("503" in msg) or ("UNAVAILABLE" in msg)
                if not retriable or attempt == 3:
                    raise
                time.sleep(1.5 * (2 ** attempt))
        raise last_err  # pragma: no cover