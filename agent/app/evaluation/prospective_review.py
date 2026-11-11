from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from app.evaluation.prospective_collection import validate_report


def _cohort_metrics(summary: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "observations": int(summary.get("observations", 0)),
        "pending": int(summary.get("pending", 0)),
        "matured": int(summary.get("matured", 0)),
        "average_net_return_pct": summary.get("average_net_return_pct"),
        "median_net_return_pct": summary.get("median_net_return_pct"),
        "positive_return_rate_pct": summary.get("positive_return_rate_pct"),
    }


def build_review(report: Mapping[str, Any]) -> dict[str, Any]:
    validate_report(report)

    baseline = _cohort_metrics(report.get("baseline") or {})
    candidate = _cohort_metrics(report.get("candidate_summary") or {})
    minimum = int(report["min_matured_observations"])
    matured = candidate["matured"]
    sample_ready = bool(report.get("sample_ready"))

    if sample_ready:
        state = "REVIEW_REQUIRED"
        decision = "REVIEW"
        reason = (
            "Minimum matured candidate sample reached; formal human review is required "
            "before any Phase 6 decision."
        )
    elif candidate["observations"] == 0:
        state = "WAITING_FOR_CANDIDATE_SIGNAL"
        decision = "WAIT"
        reason = "No qualifying frozen-candidate observation has been recorded yet."
    elif candidate["matured"] == 0:
        state = "WAITING_FOR_MATURITY"
        decision = "WAIT"
        reason = "Candidate observations exist but none has a complete 24h outcome yet."
    else:
        state = "ACCUMULATING_MATURED_SAMPLE"
        decision = "WAIT"
        reason = (
            f"{matured} of {minimum} matured candidate observations collected; "
            "continue prospective evidence collection."
        )

    progress_pct = min(100.0, matured / minimum * 100.0)

    frozen = report["candidate"]
    return {
        "phase": "5G.2-monitoring-review",
        "source_created_at": (report.get("metadata") or {}).get("created_at"),
        "as_of_ms": int(report["as_of_ms"]),
        "decision": decision,
        "state": state,
        "reason": reason,
        "phase6_blocked": True,
        "sample_ready": sample_ready,
        "progress": {
            "matured_candidate_observations": matured,
            "required_matured_candidate_observations": minimum,
            "percent": progress_pct,
            "remaining": max(0, minimum - matured),
        },
        "milestones": {
            "first_baseline_observation": baseline["observations"] > 0,
            "first_candidate_observation": candidate["observations"] > 0,
            "first_candidate_matured": candidate["matured"] > 0,
            "sample_ready": sample_ready,
        },
        "baseline": baseline,
        "candidate": candidate,
        "uplift_vs_baseline_pct_points": report.get(
            "uplift_vs_baseline_pct_points"
        ),
        "frozen_experiment": {
            "symbol": frozen["symbol"],
            "feature": frozen["feature"],
            "operator": frozen["operator"],
            "value": frozen["value"],
            "frozen_at_ms": int(report["frozen_at_ms"]),
            "outcome_hours": int(report["outcome_hours"]),
        },
        "guardrails": {
            "automatic_promotion": False,
            "strategy_changes_allowed": False,
            "execution_enabled": False,
            "private_binance_api": False,
        },
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5G.2 prospective monitoring and human-review gate"
    )
    parser.add_argument("--input", default="reports/phase5g/latest.json")
    parser.add_argument("--output", default="reports/phase5g/review.json")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    source = Path(args.input)
    report = json.loads(source.read_text(encoding="utf-8"))
    review = build_review(report)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(review, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    progress = review["progress"]
    print(
        f"{review['decision']} | {review['state']} | "
        f"candidate matured {progress['matured_candidate_observations']}/"
        f"{progress['required_matured_candidate_observations']} "
        f"({progress['percent']:.1f}%)"
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
