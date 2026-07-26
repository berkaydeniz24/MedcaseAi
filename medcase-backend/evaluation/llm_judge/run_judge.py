# evaluation/llm_judge/run_judge.py
"""
Runs the LLM-as-a-Judge (judge_agent.py) over the same blinded 24-case set
used by the Human Expert Evaluation form (evaluation/human_eval/), so LLM
and human scores are directly comparable later — same cases, same "Item 1"/
"Item 2" units, same 5-criterion rubric. The judge is only ever given
content, never a system label (blind by construction).

Writes two outputs:
  judge_scores.json — full structured scores + justifications + concerns.
  judge_scores.csv  — same column shape as a human rater's exported CSV
                       (rater_name="LLM-Judge (<model>)"), so Week 6 analysis
                       can concatenate LLM + human CSVs directly.

Unlike the human eval form, this script has legitimate access to
unblinding_key.json (it's our own automation, not a rater) — so it also
prints a per-system aggregate as an early signal. This is NOT a substitute
for the Week 6 analysis once real human CSVs exist; it's a sanity check the
judge itself is behaving reasonably before handing the form to raters.

Usage:
    cd medcase-backend
    python3 -m evaluation.llm_judge.run_judge
"""
import csv
import json
import os
import statistics
from collections import defaultdict
from datetime import datetime, timezone

from .judge_agent import LLMJudge

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HUMAN_EVAL_DIR = os.path.normpath(os.path.join(BASE_DIR, "..", "human_eval"))
BLINDED_SET_PATH = os.path.join(HUMAN_EVAL_DIR, "blinded_eval_set.json")
UNBLINDING_KEY_PATH = os.path.join(HUMAN_EVAL_DIR, "unblinding_key.json")

CRITERIA = ["clinical_correctness", "relevance", "consistency", "educational_usefulness", "clarity"]


def main():
    with open(BLINDED_SET_PATH, "r", encoding="utf-8") as f:
        blinded_set = json.load(f)

    judge = LLMJudge()
    rows = []  # flat records for CSV + aggregation
    full_records = []  # full JudgeScores + case metadata for JSON

    for case in blinded_set:
        for item_label, item in case["items"].items():
            scores = judge.score(
                specialty=case["specialty"],
                narrative=case["narrative"],
                question=item["question"],
                options=item["options"],
                correct_index=item["correct_index"],
                hint=item["hint"],
                explanation=item["explanation"],
                case_id=case["case_id"],
            )
            score_dict = scores.model_dump()
            avg = statistics.mean(score_dict[c]["score"] for c in CRITERIA)

            full_records.append({
                "case_id": case["case_id"],
                "item_label": item_label,
                "scores": score_dict,
                "overall_avg": round(avg, 2),
            })
            rows.append({
                "case_id": case["case_id"],
                "item_label": item_label,
                **{c: score_dict[c]["score"] for c in CRITERIA},
                "overall_avg": round(avg, 2),
                "concerns": "; ".join(score_dict["concerns"]),
            })
            print(f"OK  {case['case_id']} {item_label}  avg={avg:.2f}")

    model_name = judge.model
    now = datetime.now(timezone.utc).isoformat()

    json_path = os.path.join(BASE_DIR, "judge_scores.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"model": model_name, "prompt_version": "v1.0", "results": full_records}, f, indent=2, ensure_ascii=False)

    csv_path = os.path.join(BASE_DIR, "judge_scores.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["rater_name", "rater_role", "case_id", "item_label", *CRITERIA, "overall_avg", "comment", "exported_at"])
        for r in rows:
            writer.writerow([
                f"LLM-Judge ({model_name})", "LLM-Judge", r["case_id"], r["item_label"],
                *[r[c] for c in CRITERIA], r["overall_avg"], r["concerns"], now,
            ])

    print(f"\n{len(rows)} item scores -> {json_path}, {csv_path}")

    # Early per-system signal (legitimate here only because this script,
    # unlike a human rater, is allowed to see the unblinding key).
    if os.path.exists(UNBLINDING_KEY_PATH):
        with open(UNBLINDING_KEY_PATH, "r", encoding="utf-8") as f:
            key = json.load(f)["key"]

        by_system = defaultdict(list)
        for r in rows:
            system = key.get(r["case_id"], {}).get(r["item_label"])
            if system:
                by_system[system].append(r["overall_avg"])

        print("\n--- Early per-system signal (unblinded, judge-only, not the Week 6 report) ---")
        for system in ("single_agent", "multi_agent"):
            vals = by_system.get(system, [])
            if vals:
                print(f"{system}: n={len(vals)} mean_overall_avg={statistics.mean(vals):.2f}")
    else:
        print("\n(unblinding_key.json not found — skipping per-system signal, blind CSV/JSON still written)")


if __name__ == "__main__":
    main()
