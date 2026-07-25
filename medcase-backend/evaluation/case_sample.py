# evaluation/case_sample.py
"""
Deterministic, reproducible test-case list shared by both experiment arms
(roadmap item 3, Week 1: "Ortak test vaka listesi hazırlanır"). Both
System A (single_agent.py) and System B (multi_agent_runner.py) MUST run
against exactly the same case IDs, otherwise any measured difference could
be explained by "which cases got shown to which system" rather than by
architecture — that would break the whole comparison.

Sampling is stratified by specialty so the pilot/full samples mirror the
real specialty mix documented in docs/dataset.md (Gastroenterology,
Dermatology and Neurology are the largest groups in cases_subset.json).
"""
import json
import os
import random
from collections import defaultdict
from typing import List

from sqlalchemy.orm import Session

from services import models

DEFAULT_SEED = 42
SAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "case_samples")


def build_case_sample(db: Session, n: int, seed: int = DEFAULT_SEED) -> List[str]:
    all_cases = db.query(models.Case).order_by(models.Case.id).all()
    if n >= len(all_cases):
        return [c.id for c in all_cases]

    by_specialty = defaultdict(list)
    for c in all_cases:
        by_specialty[c.specialty].append(c)

    rng = random.Random(seed)
    total = len(all_cases)
    sample_ids = []
    for specialty in sorted(by_specialty):
        cases = by_specialty[specialty]
        share = max(1, round(n * len(cases) / total))
        picked = rng.sample(cases, min(share, len(cases)))
        sample_ids.extend(c.id for c in picked)

    rng.shuffle(sample_ids)
    return sorted(sample_ids[:n])


def save_sample(name: str, ids: List[str]) -> str:
    os.makedirs(SAMPLES_DIR, exist_ok=True)
    path = os.path.join(SAMPLES_DIR, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ids, f, ensure_ascii=False, indent=2)
    return path


def load_sample(name: str) -> List[str]:
    path = os.path.join(SAMPLES_DIR, f"{name}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    # One-off generation of the committed sample files (pilot = Week 3 plan,
    # full = Week 4 plan). Re-running this is a no-op in terms of content as
    # long as the Case table and DEFAULT_SEED don't change.
    from services.database import SessionLocal

    db = SessionLocal()
    try:
        pilot_ids = build_case_sample(db, n=10)
        full_ids = build_case_sample(db, n=50)
    finally:
        db.close()

    pilot_path = save_sample("pilot_10", pilot_ids)
    full_path = save_sample("full_50", full_ids)

    import logging
    from services.logging_config import configure_logging
    configure_logging()
    logger = logging.getLogger(__name__)
    logger.info("pilot_10 (%d cases) -> %s", len(pilot_ids), pilot_path)
    logger.info("full_50 (%d cases) -> %s", len(full_ids), full_path)
