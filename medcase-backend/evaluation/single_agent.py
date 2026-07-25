# evaluation/single_agent.py
"""
System A — Single-Agent Baseline (roadmap item 3).

One generalist agent, one prompt persona, ONE API call handles everything
the production multi-agent pipeline splits across three specialists
(MCQ Generator, Dialogue Agent, Tutor Agent): writing the question, the four
options, the correct answer, a Socratic hint, and a full explanation.

This exists purely as an experimental control arm — it is not part of the
live app. Its only job is to give evaluation/multi_agent_runner.py something
architecturally different to be compared against, while holding the model,
case set, and language constant (see docs/evaluation_plan.md for the full
controlled-variable list).
"""
import os
import time
from typing import Dict

from dotenv import load_dotenv
from google import genai

from .schemas import CallMetrics, GeneratedContent, SystemRunResult

load_dotenv()

SINGLE_AGENT_SYSTEM_PROMPT = """
You are a single, general-purpose medical education AI. Unlike a team of
specialized assistants, you alone are responsible for the entire exercise
built from one clinical case: writing the assessment question, the answer
options, identifying the correct option, writing a hint, and writing a full
explanation.

ROLE: Educational only. You are not a clinician and this is not medical
advice. Never give real-life treatment instructions.

LANGUAGE: Respond in English only, regardless of the language of the case
narrative.

You will be given a case narrative, its specialty, and its difficulty. Using
ONLY the information in the narrative (do not invent external facts),
produce ALL of the following in one response:

1. question — One assessment-quality multiple-choice clinical question that
   tests reasoning about THIS SPECIFIC case (not generic textbook trivia).
2. options — Exactly 4 plausible, clearly distinguishable answer options.
3. correct_index — The 0-based index (0-3) of the correct option.
4. hint — A short (3-7 sentence), Socratic-style hint that helps a student
   move toward the answer WITHOUT revealing which option is correct. Ask
   1-2 guiding questions. Do not state or imply the correct option.
5. explanation — A longer (8-16 sentence), fully reasoned explanation that
   DOES reveal and justify the correct option, explains why the other
   options are weaker, and ties every claim to a specific detail from the
   narrative.

CONSTRAINTS:
- Do not add external facts not supported by the narrative.
- The hint must never leak the answer; the explanation must clearly reveal
  and justify it.
- Keep the tone educational and encouraging, never like an answer key.
""".strip()


class SingleAgentBaseline:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None
        self.model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

    def run(self, case: Dict) -> SystemRunResult:
        if not self.client:
            return SystemRunResult(
                case_id=case["id"],
                system="single_agent",
                content=None,
                calls=[CallMetrics(
                    step="monolithic", model=self.model, latency_ms=0.0,
                    success=False, error="GEMINI_API_KEY missing",
                )],
            )

        prompt = self._build_prompt(case)
        start = time.perf_counter()
        try:
            resp = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": GeneratedContent,
                },
            )
            latency_ms = (time.perf_counter() - start) * 1000
            usage = resp.usage_metadata
            content = resp.parsed
            call = CallMetrics(
                step="monolithic", model=self.model, latency_ms=latency_ms,
                input_tokens=usage.prompt_token_count if usage else None,
                output_tokens=usage.candidates_token_count if usage else None,
                success=content is not None,
                error=None if content is not None else "response.parsed was empty",
            )
            return SystemRunResult(case_id=case["id"], system="single_agent", content=content, calls=[call])
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            call = CallMetrics(
                step="monolithic", model=self.model, latency_ms=latency_ms,
                success=False, error=str(e),
            )
            return SystemRunResult(case_id=case["id"], system="single_agent", content=None, calls=[call])

    def _build_prompt(self, case: Dict) -> str:
        return (
            f"{SINGLE_AGENT_SYSTEM_PROMPT}\n\n"
            f"SPECIALTY: {case.get('specialty', 'General')}\n"
            f"DIFFICULTY: {case.get('difficulty', 'Intermediate')}\n\n"
            f"CASE NARRATIVE:\n{case.get('narrative', '')}"
        )


single_agent_baseline = SingleAgentBaseline()
