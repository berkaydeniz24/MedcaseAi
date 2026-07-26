# evaluation/human_eval/build_blinded_set.py
"""
Human Expert Evaluation (roadmap item 3, Week 5): builds a blinded subset
from an existing paired single-agent/multi-agent run (default: the Week 4
full_50 run, evaluation/results/raw/full_50_n50.json) for 1-2 medical
students + a faculty/research-assistant rater to score. No new LLM calls —
this reuses outputs already generated and reviewed in Week 3/4.

Blinding: for each selected case, the two systems' outputs are randomly
assigned to "Item 1" / "Item 2" (seeded, independent per case so the
label doesn't correlate with system across the set). Two files are written:

  blinded_eval_set.json   — case narrative + Item 1 / Item 2 content only,
                             no system labels. This is what raters see
                             (embedded into rating_form.html). Safe to commit.
  unblinding_key.json     — case_id -> {"Item 1": system, "Item 2": system}.
                             Needed later to compute per-system scores.
                             NOT shown to raters — gitignored.

Usage:
    cd medcase-backend
    python3 -m evaluation.human_eval.build_blinded_set
    python3 -m evaluation.human_eval.build_blinded_set --n 24 --seed 7 \
        --source evaluation/results/raw/full_50_n50.json
"""
import argparse
import json
import os
import random

from services.database import SessionLocal
from services import models

HUMAN_EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SOURCE = os.path.normpath(
    os.path.join(HUMAN_EVAL_DIR, "..", "results", "raw", "full_50_n50.json")
)
DEFAULT_N = 24
DEFAULT_SEED = 7  # deliberately different from case_sample.py's seed=42 —
# this is an independent randomization (which cases + which item label),
# not the case-selection step itself.


def load_paired_results(source_path: str):
    with open(source_path, "r", encoding="utf-8") as f:
        rows = json.load(f)

    by_case = {}
    for row in rows:
        if row.get("failed"):
            continue
        by_case.setdefault(row["case_id"], {})[row["system"]] = row

    return {
        cid: systems for cid, systems in by_case.items()
        if "single_agent" in systems and "multi_agent" in systems
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=DEFAULT_N)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    args = parser.parse_args()

    paired = load_paired_results(args.source)
    if args.n > len(paired):
        raise SystemExit(f"Requested n={args.n} but only {len(paired)} cases have complete paired results")

    rng = random.Random(args.seed)
    selected_ids = sorted(rng.sample(sorted(paired.keys()), args.n))

    # Force an exactly balanced assignment (half the cases get Item 1 =
    # multi_agent, half get Item 1 = single_agent) rather than an
    # independent per-case coin flip — at n=24 a fair coin flip can land
    # lopsided (e.g. 16/8) by chance, which would leave "Item 1" itself
    # weakly correlated with system. Balancing removes that as a possible
    # confound entirely rather than just hoping the flips even out.
    half = args.n // 2
    item1_system = ["multi_agent"] * half + ["single_agent"] * (args.n - half)
    rng.shuffle(item1_system)

    db = SessionLocal()
    blinded_set = []
    unblinding_key = {}

    for case_id, item1 in zip(selected_ids, item1_system):
        row = db.query(models.Case).filter(models.Case.id == case_id).first()
        if row is None:
            continue

        systems = paired[case_id]
        item2 = "single_agent" if item1 == "multi_agent" else "multi_agent"
        item_map = {"Item 1": item1, "Item 2": item2}
        unblinding_key[case_id] = item_map

        def content_of(system_name):
            r = systems[system_name]
            return {
                "question": r["question"],
                "options": r["options"],
                "correct_index": r["correct_index"],
                "hint": r["hint"],
                "explanation": r["explanation"],
            }

        blinded_set.append({
            "case_id": case_id,
            "title": row.title,
            "specialty": row.specialty,
            "narrative": row.narrative,
            "items": {
                "Item 1": content_of(item_map["Item 1"]),
                "Item 2": content_of(item_map["Item 2"]),
            },
        })

    db.close()

    blinded_path = os.path.join(HUMAN_EVAL_DIR, "blinded_eval_set.json")
    key_path = os.path.join(HUMAN_EVAL_DIR, "unblinding_key.json")

    with open(blinded_path, "w", encoding="utf-8") as f:
        json.dump(blinded_set, f, indent=2, ensure_ascii=False)

    with open(key_path, "w", encoding="utf-8") as f:
        json.dump({
            "source": args.source,
            "seed": args.seed,
            "key": unblinding_key,
        }, f, indent=2, ensure_ascii=False)

    print(f"{len(blinded_set)} cases -> {blinded_path}")
    print(f"unblinding key -> {key_path} (do not share with raters)")


if __name__ == "__main__":
    main()
