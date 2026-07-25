# evaluation/automated_checks.py
"""
Automated Evaluation layer (roadmap item 3/4, Week 2: "Otomatik metrikler
yazılır"). Pure, code-only checks over a SystemRunResult's content — no LLM
calls, no human judgement.

These are intentionally coarse: they catch GROSS structural problems
(duplicate options, an answer that leaks into the question or hint) that
don't require clinical judgement to detect. They do NOT assess clinical
correctness, explanation quality, or nuanced consistency — that's what the
LLM-as-a-Judge and Human Expert layers (docs/evaluation_plan.md §3.2/§3.3,
Weeks 5+) are for. Treat every flag here as "worth a human's attention",
not as ground truth.
"""
import re
from typing import List, Optional

from .schemas import AutomatedChecks, SystemRunResult

# Generic MCQ/clinical boilerplate that would otherwise cause false-positive
# "leak" detections just from shared phrasing rather than shared meaning
# (e.g. every option in a case about an elderly patient will legitimately
# contain "patient", "history", "findings", etc.).
_STOPWORDS = {
    "this", "that", "these", "those", "with", "from", "have", "which", "most",
    "likely", "following", "patient", "presents", "presented", "presenting",
    "case", "narrative", "diagnosis", "finding", "findings", "clinical",
    "history", "consistent", "given", "based", "would", "should", "could",
    "years", "year", "old", "male", "female", "shows", "showed", "reveals",
    "revealed", "associated", "underlying", "condition", "disease", "upon",
    "examination", "evaluation", "evaluating", "options", "option", "correct",
}

# Explanations should reuse a good chunk of the correct option's distinctive
# vocabulary (otherwise it may be explaining a different answer than the one
# it claims is correct). Hint/question reusing even less than that already
# looks like a plausible leak — thresholds differ on purpose: grounding
# needs stronger evidence, leaking needs a lower bar to be worth flagging.
GROUNDING_THRESHOLD = 0.4
LEAK_THRESHOLD = 0.3


def _words(text: str) -> set:
    return {w for w in re.findall(r"[a-zA-Z]{4,}", (text or "").lower())} - _STOPWORDS


def _distinctive_words(options: List[str], idx: int) -> set:
    """Words in the correct option that don't also appear in any distractor —
    i.e. the vocabulary that would specifically identify it as correct."""
    target = _words(options[idx])
    others = set()
    for i, opt in enumerate(options):
        if i != idx:
            others |= _words(opt)
    return target - others


def _overlap_fraction(distinctive: set, text: str) -> Optional[float]:
    if not distinctive:
        return None
    hits = sum(1 for w in distinctive if w in _words(text))
    return hits / len(distinctive)


def compute_automated_checks(result: SystemRunResult) -> AutomatedChecks:
    content = result.content
    if content is None:
        return AutomatedChecks(
            schema_valid=False,
            option_count_ok=False,
            has_empty_option=False,
            has_duplicate_options=False,
            correct_index_in_range=False,
            flags=["generation_failed"],
        )

    flags: List[str] = []
    options = content.options
    idx = content.correct_index

    option_count_ok = len(options) == 4
    if not option_count_ok:
        flags.append("wrong_option_count")

    normalized = [o.strip().lower() for o in options]
    has_empty_option = any(not o for o in normalized)
    if has_empty_option:
        flags.append("empty_option")

    has_duplicate_options = len(set(normalized)) < len(normalized)
    if has_duplicate_options:
        flags.append("duplicate_options")

    correct_index_in_range = 0 <= idx < len(options)
    if not correct_index_in_range:
        flags.append("correct_index_out_of_range")

    explanation_grounds: Optional[bool] = None
    hint_leaks: Optional[bool] = None
    answer_leaked_in_question: Optional[bool] = None

    if correct_index_in_range and option_count_ok:
        distinctive = _distinctive_words(options, idx)
        if not distinctive:
            # The correct option shares its entire (non-stopword) vocabulary
            # with the distractors — grounding/leak checks would be
            # meaningless here, and the MCQ itself is suspect either way.
            flags.append("low_option_distinctiveness")
        else:
            exp_overlap = _overlap_fraction(distinctive, content.explanation)
            explanation_grounds = exp_overlap is not None and exp_overlap >= GROUNDING_THRESHOLD
            if explanation_grounds is False:
                flags.append("explanation_not_grounded_in_correct_option")

            hint_overlap = _overlap_fraction(distinctive, content.hint)
            hint_leaks = hint_overlap is not None and hint_overlap >= LEAK_THRESHOLD
            if hint_leaks:
                flags.append("possible_answer_leak_in_hint")

            q_overlap = _overlap_fraction(distinctive, content.question)
            answer_leaked_in_question = q_overlap is not None and q_overlap >= LEAK_THRESHOLD
            if answer_leaked_in_question:
                flags.append("possible_answer_leak_in_question")

    return AutomatedChecks(
        schema_valid=True,
        option_count_ok=option_count_ok,
        has_empty_option=has_empty_option,
        has_duplicate_options=has_duplicate_options,
        correct_index_in_range=correct_index_in_range,
        explanation_grounds_correct_option=explanation_grounds,
        hint_leaks_correct_option=hint_leaks,
        answer_leaked_in_question=answer_leaked_in_question,
        flags=flags,
    )
