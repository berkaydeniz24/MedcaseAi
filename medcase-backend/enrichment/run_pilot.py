# enrichment/run_pilot.py
"""
Rubric enrichment pilot: runs RubricAgent on the same 10-case cohort used by
evaluation/case_samples/pilot_10.json (so this pilot and the eval pilot are
directly comparable later) and writes a review file for human QC. Does NOT
write to the `cases` table by default — see docs/dataset.md's sequencing:
pilot -> QC pass -> full 200-case batch.

Usage:
    cd medcase-backend
    python3 -m enrichment.run_pilot              # dry run, writes review JSON only
    python3 -m enrichment.run_pilot --commit      # also writes into the DB for these 10 cases
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone

from services.database import SessionLocal
from services.logging_config import configure_logging
from services import models

from .rubric_agent import RubricAgent

configure_logging()
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PILOT_IDS_PATH = os.path.normpath(
    os.path.join(BASE_DIR, "..", "evaluation", "case_samples", "pilot_10.json")
)
RESULTS_DIR = os.path.normpath(
    os.path.join(BASE_DIR, "..", "evaluation", "results", "raw")
)


def load_pilot_case_ids():
    with open(PILOT_IDS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", action="store_true",
                         help="Write results into the cases table (default: review file only)")
    args = parser.parse_args()

    case_ids = load_pilot_case_ids()
    db = SessionLocal()
    agent = RubricAgent()

    results = []
    failures = []

    for case_id in case_ids:
        row = db.query(models.Case).filter(models.Case.id == case_id).first()
        if row is None:
            logger.error("run_pilot: case_id=%s not found in DB, skipping", case_id)
            failures.append({"case_id": case_id, "error": "not found in DB"})
            continue

        try:
            enriched = agent.enrich(case_id=row.id, specialty=row.specialty, narrative=row.narrative)
        except Exception as e:
            logger.error("run_pilot: enrichment failed for case_id=%s: %s", case_id, e)
            failures.append({"case_id": case_id, "error": str(e)})
            continue

        record = {
            "case_id": row.id,
            "title": row.title,
            "specialty": row.specialty,
            "narrative": row.narrative,
            "previous_difficulty": row.difficulty,
            "enriched": enriched.model_dump(),
        }
        results.append(record)
        print(f"OK  {case_id}  difficulty={enriched.difficulty}")

        if args.commit:
            row.difficulty = enriched.difficulty
            row.rubric_json = json.dumps({
                "chief_complaint": enriched.chief_complaint,
                "red_flags": enriched.red_flags,
                "ddx_top": enriched.ddx_top,
                "tests_initial": enriched.tests_initial,
                "management_initial": enriched.management_initial,
                "pitfalls": enriched.pitfalls,
            }, ensure_ascii=False)
            row.seed_questions_json = json.dumps(enriched.seed_questions, ensure_ascii=False)

    if args.commit:
        db.commit()
        logger.info("run_pilot: committed %d enriched cases to DB", len(results))

    os.makedirs(RESULTS_DIR, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = os.path.join(RESULTS_DIR, f"rubric_pilot_{timestamp}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "prompt_version": "v1.0",
            "committed_to_db": args.commit,
            "results": results,
            "failures": failures,
        }, f, indent=2, ensure_ascii=False)

    print(f"\n{len(results)}/{len(case_ids)} cases enriched, {len(failures)} failures.")
    print(f"Review file: {out_path}")
    if args.commit:
        print("Committed to DB.")
    else:
        print("Dry run only — DB not modified. Re-run with --commit after QC.")

    db.close()
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
