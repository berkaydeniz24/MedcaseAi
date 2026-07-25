# evaluation/charts.py
"""
Chart generation for the Automated Evaluation layer (roadmap item 3/4,
Week 2 follow-up). Produces the latency/token comparison charts that are
measurable today from evaluation/run_experiment.py's summary dict.

Deliberately does NOT produce an accuracy.png: accuracy/clinical-correctness
scoring doesn't exist yet (that's the LLM-as-a-Judge and Human Expert layers,
docs/evaluation_plan.md §3.2-3.3, Weeks 5-6) — faking a chart from data that
isn't there would misrepresent the project's actual progress.
"""
import os
from typing import Dict, List

import matplotlib
matplotlib.use("Agg")  # headless — this runs from a CLI script, no display
import matplotlib.pyplot as plt

SYSTEM_LABELS = {"single_agent": "Single-Agent", "multi_agent": "Multi-Agent"}
SYSTEM_COLORS = {"single_agent": "#4C72B0", "multi_agent": "#DD8452"}


def _bar_chart(title: str, ylabel: str, values_by_system: Dict[str, float], out_path: str) -> None:
    systems = [s for s in ("single_agent", "multi_agent") if s in values_by_system]
    labels = [SYSTEM_LABELS[s] for s in systems]
    values = [values_by_system[s] for s in systems]
    colors = [SYSTEM_COLORS[s] for s in systems]

    fig, ax = plt.subplots(figsize=(5, 4))
    bars = ax.bar(labels, values, color=colors)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.bar_label(bars, fmt="%.0f", padding=3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def generate_charts(summary: Dict[str, Dict], out_dir: str, base: str) -> List[str]:
    os.makedirs(out_dir, exist_ok=True)
    written = []

    latency = {s: summary[s]["mean_latency_ms"] for s in summary}
    if latency:
        path = os.path.join(out_dir, f"{base}_latency.png")
        _bar_chart("Mean Latency per Case", "Latency (ms)", latency, path)
        written.append(path)

    tokens = {s: summary[s]["mean_total_tokens"] for s in summary}
    if tokens:
        path = os.path.join(out_dir, f"{base}_token_usage.png")
        _bar_chart("Mean Total Tokens per Case", "Tokens (input + output)", tokens, path)
        written.append(path)

    calls = {s: summary[s]["mean_api_calls"] for s in summary}
    if calls:
        path = os.path.join(out_dir, f"{base}_api_calls.png")
        _bar_chart("Mean API Calls per Case", "API calls", calls, path)
        written.append(path)

    return written
