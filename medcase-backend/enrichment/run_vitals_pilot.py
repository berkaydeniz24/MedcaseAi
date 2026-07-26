# enrichment/run_vitals_pilot.py
"""
Vitals extraction pilot: runs VitalsAgent on the same 10-case cohort as
the rubric pilot (evaluation/case_samples/pilot_10.json) and writes a
review file for human QC. Does NOT write to the `cases` table by default —
same pilot -> QC -> scale-up sequencing as enrichment/run_pilot.py.

An empty result (no vitals extracted) is expected for some/most cases —
only ~37% of all 200 narratives mention any vital sign at all (checked
before building this). That is NOT a failure, just printed as "0 vitals".

Usage:
    cd medcase-backend
    python3 -m enrichment.run_vitals_pilot              # dry run
    python3 -m enrichment.run_vitals_pilot --commit      # write into DB for these 10 cases
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

from .vitals_agent import VitalsAgent

configure_logging()
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PILOT_IDS_PATH = os.path.normpath(
    os.path.join(BASE_DIR, "..", "evaluation", "case_samples", "pilot_10.json")
)
RESULTS_DIR = os.path.normpath(
    os.path.join(BASE_DIR, "..", "evaluation", "results", "raw")
)

VITAL_FIELDS = ["temperature", "heart_rate", "blood_pressure", "respiratory_rate", "spo2"]


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
    agent = VitalsAgent()

    results = []
    failures = []
    total_vitals_found = 0

    for case_id in case_ids:
        row = db.query(models.Case).filter(models.Case.id == case_id).first()
        if row is None:
            logger.error("run_vitals_pilot: case_id=%s not found in DB, skipping", case_id)
            failures.append({"case_id": case_id, "error": "not found in DB"})
            continue

        try:
            extracted = agent.extract(case_id=row.id, narrative=row.narrative)
        except Exception as e:
            logger.error("run_vitals_pilot: extraction failed for case_id=%s: %s", case_id, e)
            failures.append({"case_id": case_id, "error": str(e)})
            continue

        vitals_dict = {
            f: getattr(extracted, f).model_dump()
            for f in VITAL_FIELDS if getattr(extracted, f) is not None
        }
        total_vitals_found += len(vitals_dict)

        results.append({
            "case_id": row.id,
            "title": row.title,
            "narrative": row.narrative,
            "vitals": vitals_dict,
        })
        print(f"OK  {case_id}  {len(vitals_dict)} vital(s): {list(vitals_dict.keys())}")

        if args.commit:
            row.vitals_json = json.dumps(vitals_dict, ensure_ascii=False)

    if args.commit:
        db.commit()
        logger.info("run_vitals_pilot: committed %d cases to DB", len(results))

    os.makedirs(RESULTS_DIR, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = os.path.join(RESULTS_DIR, f"vitals_pilot_{timestamp}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "prompt_version": "v1.0",
            "committed_to_db": args.commit,
            "results": results,
            "failures": failures,
        }, f, indent=2, ensure_ascii=False)

    print(f"\n{len(results)}/{len(case_ids)} cases processed, {len(failures)} failures, "
          f"{total_vitals_found} total vital readings found.")
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
