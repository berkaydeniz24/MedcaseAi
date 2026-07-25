# evaluation/single_agent.py
"""
System A — Single-Agent Baseline (roadmap item 3).

One generalist agent, one prompt persona, ONE API call handles everything
the production multi-agent pipeline splits across three specialists
(MCQ Agent, Dialogue Agent, Tutor Agent): writing the question, the four
options, the correct answer, a Socratic hint, and a full explanation.

This exists purely as an experimental control arm — it is not part of the
live app. Its only job is to give evaluation/multi_agent_runner.py something
architecturally different to be compared against, while holding the model,
case set, and language constant (see docs/evaluation_plan.md for the full
controlled-variable list).
"""
import logging
import os
import time
from typing import Dict

from services.gemini_client import GeminiClient
from services.prompt_loader import load_prompt

from .schemas import CallMetrics, GeneratedContent, SystemRunResult

logger = logging.getLogger(__name__)

PROMPT_VERSION = "v1.0"


class SingleAgentBaseline:
    def __init__(self):
        try:
            self.client = GeminiClient().client
        except Exception as e:
            logger.warning("SingleAgentBaseline: client init failed: %s", e)
            self.client = None
        self.model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
        self._template = load_prompt("single_agent_baseline", PROMPT_VERSION)

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
            logger.info(
                "single_agent: generating for case_id=%s prompt_version=%s",
                case.get("id"), PROMPT_VERSION,
            )
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
            logger.error("single_agent: generation failed for case_id=%s: %s", case.get("id"), e)
            call = CallMetrics(
                step="monolithic", model=self.model, latency_ms=latency_ms,
                success=False, error=str(e),
            )
            return SystemRunResult(case_id=case["id"], system="single_agent", content=None, calls=[call])

    def _build_prompt(self, case: Dict) -> str:
        return self._template.substitute(
            specialty=case.get("specialty", "General"),
            difficulty=case.get("difficulty", "Intermediate"),
            narrative=case.get("narrative", ""),
        )


single_agent_baseline = SingleAgentBaseline()
