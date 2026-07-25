# services/gemini_client.py
"""
Single, shared entry point for constructing a Gemini client. Previously
dialogue/gemini_client.py, tutor/gemini_client.py and services/mcq_generator.py
each built their own `genai.Client(api_key=...)` independently — same key,
three separate code paths. All agents now go through this module instead.

`.client` exposes the raw google-genai Client so callers needing structured
output (response_mime_type/response_schema) or evaluation harness
instrumentation (evaluation/multi_agent_runner.py patches
`client.models.generate_content` per call) keep working unchanged.
`.generate()` is an optional plain-text convenience path with retry/backoff
on transient errors (429/503) for callers that don't need a schema.
"""
import os
import time
from typing import Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

_shared_client: Optional[genai.Client] = None


def get_gemini_client() -> genai.Client:
    """The one shared raw genai.Client, built once from GEMINI_API_KEY."""
    global _shared_client
    if _shared_client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        _shared_client = genai.Client(api_key=api_key)
    return _shared_client


class GeminiClient:
    def __init__(self):
        self.client = get_gemini_client()

    def generate(
        self,
        system: str,
        user: str,
        model: str,
        temperature: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
        timeout_s: int = 25,
    ) -> str:
        """
        Plain-text generation with retry/backoff. temperature/max_output_tokens
        are None (unset) by default so callers that don't pass them get the
        model's own defaults — important for evaluation/*: the single-agent
        vs multi-agent comparison is only fair if neither arm silently
        overrides generation parameters (see docs/evaluation_plan.md §1).
        """
        config_kwargs = {"system_instruction": system}
        if temperature is not None:
            config_kwargs["temperature"] = temperature
        if max_output_tokens is not None:
            config_kwargs["max_output_tokens"] = max_output_tokens

        last_err = None
        for attempt in range(4):
            try:
                resp = self.client.models.generate_content(
                    model=model,
                    contents=[types.Content(role="user", parts=[types.Part(text=user)])],
                    config=types.GenerateContentConfig(**config_kwargs),
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
