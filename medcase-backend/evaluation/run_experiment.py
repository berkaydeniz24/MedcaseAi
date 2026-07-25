# evaluation/run_experiment.py
"""
Week 2 — Evaluation Pipeline (roadmap item 3: "Otomatik metrikler yazılır.
Latency ve token logging eklenir. Deney sonuçları JSON veya CSV olarak
kaydedilir.").

Runs both experimental arms (single_agent, multi_agent) over a shared case
sample, attaches the Automated Evaluation layer's checks
(evaluation/automated_checks.py) to every result, and writes:
  - a detailed JSON (every SystemRunResult + AutomatedChecks)
  - a per-case-per-system CSV (one row per run)
  - an aggregated summary CSV — the "Ana sonuç tablosu" shape from
    docs/evaluation_plan.md (Metric | Single-Agent | Multi-Agent)

Supersedes evaluation/run_pilot.py (Week 1's smoke test) — same underlying
calls, now scored and logged properly.

Usage:
    python3 -m evaluation.run_experiment --sample pilot_10 --limit 2
    python3 -m evaluation.run_experiment --sample pilot_10
    python3 -m evaluation.run_experiment --sample full_50 --limit 10
"""
import argparse
import csv
import json
import os
import statistics
from typing import Dict, List

from case_selector.selector_agent import selector_agent
from services.database import SessionLocal

from .automated_checks import compute_automated_checks
from .case_sample import load_sample
from .multi_agent_runner import multi_agent_runner
from .single_agent import single_agent_baseline

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
SYSTEMS = ("single_agent", "multi_agent")


def run_all(case_ids: List[str]) -> List[Dict]:
    db = SessionLocal()
    records = []
    try:
        for case_id in case_ids:
            case = selector_agent.get_case_by_id(db, case_id)
            if not case:
                print(f"SKIP {case_id}: not found in DB")
                continue
            print(f"=== {case_id} ({case['specialty']}) ===")
            for runner in (single_agent_baseline, multi_agent_runner):
                result = runner.run(case)
                checks = compute_automated_checks(result)
                record = result.to_summary_dict()
                record["automated_checks"] = checks.model_dump()
                records.append(record)
                print(f"  {result.system:12s} failed={result.failed} calls={result.total_api_calls} "
                      f"latency={result.total_latency_ms:.0f}ms flags={checks.flags or '-'}")
    finally:
        db.close()
    return records


def write_json(records: List[Dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def write_detail_csv(records: List[Dict], path: str) -> None:
    if not records:
        return
    fieldnames = list(records[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            row = dict(r)
            row["options"] = " | ".join(row.get("options") or [])
            row["automated_checks"] = json.dumps(row.get("automated_checks") or {}, ensure_ascii=False)
            writer.writerow(row)


def summarize(records: List[Dict]) -> Dict[str, Dict]:
    by_system = {s: [r for r in records if r["system"] == s] for s in SYSTEMS}

    summary = {}
    for system, rows in by_system.items():
        n = len(rows)
        if n == 0:
            continue
        failed = sum(1 for r in rows if r["failed"])
        latencies = [r["total_latency_ms"] for r in rows]
        in_tokens = [r["total_input_tokens"] for r in rows]
        out_tokens = [r["total_output_tokens"] for r in rows]
        calls = [r["total_api_calls"] for r in rows]
        total_tokens = [i + o for i, o in zip(in_tokens, out_tokens)]

        flag_counts: Dict[str, int] = {}
        for r in rows:
            for flag in r["automated_checks"].get("flags", []):
                flag_counts[flag] = flag_counts.get(flag, 0) + 1

        summary[system] = {
            "n": n,
            "failure_rate": round(failed / n, 3),
            "mean_latency_ms": round(statistics.mean(latencies), 1),
            "median_latency_ms": round(statistics.median(latencies), 1),
            "mean_api_calls": round(statistics.mean(calls), 2),
            "mean_input_tokens": round(statistics.mean(in_tokens), 1),
            "mean_output_tokens": round(statistics.mean(out_tokens), 1),
            "mean_total_tokens": round(statistics.mean(total_tokens), 1),
            "flag_counts": flag_counts,
        }
    return summary


def write_summary_csv(summary: Dict[str, Dict], path: str) -> None:
    metrics = [
        "n", "failure_rate", "mean_latency_ms", "median_latency_ms",
        "mean_api_calls", "mean_input_tokens", "mean_output_tokens", "mean_total_tokens",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Metric", "Single-Agent", "Multi-Agent"])
        for m in metrics:
            writer.writerow([
                m,
                summary.get("single_agent", {}).get(m, ""),
                summary.get("multi_agent", {}).get(m, ""),
            ])

        all_flags = sorted(
            set(summary.get("single_agent", {}).get("flag_counts", {}))
            | set(summary.get("multi_agent", {}).get("flag_counts", {}))
        )
        for flag in all_flags:
            writer.writerow([
                f"flag: {flag}",
                summary.get("single_agent", {}).get("flag_counts", {}).get(flag, 0),
                summary.get("multi_agent", {}).get("flag_counts", {}).get(flag, 0),
            ])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", default="pilot_10")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    case_ids = load_sample(args.sample)
    if args.limit:
        case_ids = case_ids[: args.limit]

    records = run_all(case_ids)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    base = f"{args.sample}_n{len(case_ids)}"
    json_path = os.path.join(RESULTS_DIR, f"{base}.json")
    detail_csv_path = os.path.join(RESULTS_DIR, f"{base}_detail.csv")
    summary_csv_path = os.path.join(RESULTS_DIR, f"{base}_summary.csv")

    write_json(records, json_path)
    write_detail_csv(records, detail_csv_path)
    summary = summarize(records)
    write_summary_csv(summary, summary_csv_path)

    print("\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2))
    print(f"\nSaved:\n  {json_path}\n  {detail_csv_path}\n  {summary_csv_path}")


if __name__ == "__main__":
    main()
