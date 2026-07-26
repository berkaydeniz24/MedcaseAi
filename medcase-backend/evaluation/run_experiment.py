# evaluation/run_experiment.py
"""
Week 2 — Evaluation Pipeline (roadmap item 3: "Otomatik metrikler yazılır.
Latency ve token logging eklenir. Deney sonuçları JSON veya CSV olarak
kaydedilir.").

Runs both experimental arms (single_agent, multi_agent) over a shared case
sample, attaches the Automated Evaluation layer's checks
(evaluation/automated_checks.py) to every result, and writes into
evaluation/results/:
  - raw/<name>.json        — every SystemRunResult + AutomatedChecks
  - processed/<name>_detail.csv  — one row per case per system
  - processed/<name>_summary.csv — the "Ana sonuç tablosu" shape from
    docs/evaluation_plan.md (Metric | Single-Agent | Multi-Agent)
  - charts/<name>_*.png    — latency/token/API-call comparison bar charts
    (evaluation/charts.py). No accuracy.png yet — that needs the scoring
    layer from Weeks 5-6, faking it would misrepresent progress.

Supersedes evaluation/run_pilot.py (Week 1's smoke test) — same underlying
calls, now scored, logged and charted properly.

Usage:
    python3 -m evaluation.run_experiment --sample pilot_10 --limit 2
    python3 -m evaluation.run_experiment --sample pilot_10
    python3 -m evaluation.run_experiment --sample full_50 --limit 10
"""
import argparse
import csv
import json
import logging
import os
import statistics
from typing import Dict, List

from case_selector.selector_agent import selector_agent
from services.database import SessionLocal
from services.logging_config import configure_logging

from .automated_checks import compute_automated_checks
from .case_sample import load_sample
from .charts import generate_charts
from .multi_agent_runner import multi_agent_runner
from .single_agent import single_agent_baseline

configure_logging()
logger = logging.getLogger(__name__)

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
RAW_DIR = os.path.join(RESULTS_DIR, "raw")
PROCESSED_DIR = os.path.join(RESULTS_DIR, "processed")
CHARTS_DIR = os.path.join(RESULTS_DIR, "charts")
SYSTEMS = ("single_agent", "multi_agent")


def run_all(case_ids: List[str]) -> List[Dict]:
    db = SessionLocal()
    records = []
    try:
        for case_id in case_ids:
            case = selector_agent.get_case_by_id(db, case_id)
            if not case:
                logger.warning("SKIP %s: not found in DB", case_id)
                continue
            logger.info("=== %s (%s) ===", case_id, case["specialty"])
            for runner in (single_agent_baseline, multi_agent_runner):
                result = runner.run(case)
                checks = compute_automated_checks(result)
                record = result.to_summary_dict()
                record["automated_checks"] = checks.model_dump()
                # Keep source/license metadata attached to every experiment
                # record — without this, a results CSV can't be traced back
                # to which cases (and whose licenses) it actually covered.
                record["source"] = case.get("source")
                records.append(record)
                logger.info(
                    "  %-12s failed=%s calls=%s latency=%.0fms flags=%s",
                    result.system, result.failed, result.total_api_calls,
                    result.total_latency_ms, checks.flags or "-",
                )
    finally:
        db.close()
    return records


def write_json(records: List[Dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def write_detail_csv(records: List[Dict], path: str) -> None:
    if not records:
        return
    # Flatten "source" into two plain columns for spreadsheet review instead
    # of a JSON blob; the full nested object is still in the raw JSON output.
    fieldnames = [k for k in records[0].keys() if k != "source"] + ["license_name", "citation_text"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            row = {k: v for k, v in r.items() if k != "source"}
            row["options"] = " | ".join(row.get("options") or [])
            row["automated_checks"] = json.dumps(row.get("automated_checks") or {}, ensure_ascii=False)
            source = r.get("source") or {}
            row["license_name"] = source.get("license_name")
            row["citation_text"] = source.get("citation_text")
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

    for d in (RAW_DIR, PROCESSED_DIR, CHARTS_DIR):
        os.makedirs(d, exist_ok=True)
    base = f"{args.sample}_n{len(case_ids)}"
    json_path = os.path.join(RAW_DIR, f"{base}.json")
    detail_csv_path = os.path.join(PROCESSED_DIR, f"{base}_detail.csv")
    summary_csv_path = os.path.join(PROCESSED_DIR, f"{base}_summary.csv")

    write_json(records, json_path)
    write_detail_csv(records, detail_csv_path)
    summary = summarize(records)
    write_summary_csv(summary, summary_csv_path)
    chart_paths = generate_charts(summary, CHARTS_DIR, base)

    logger.info("=== SUMMARY ===")
    logger.info(json.dumps(summary, indent=2))
    saved = "\n  ".join([json_path, detail_csv_path, summary_csv_path, *chart_paths])
    logger.info("Saved:\n  %s", saved)


if __name__ == "__main__":
    main()
