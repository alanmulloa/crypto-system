from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from app.evaluation.prospective_collection import validate_report

MIN_POSITIVE_RATE_PCT = 50.0


def _criterion(value: float | None, threshold: float, *, strict: bool = True) -> bool | None:
    if value is None:
        return None
    return float(value) > threshold if strict else float(value) >= threshold


def build_decision(report: Mapping[str, Any]) -> dict[str, Any]:
    validate_report(report)

    candidate = report.get("candidate_summary") or {}
    baseline = report.get("baseline") or {}
    matured = int(candidate.get("matured", 0))
    required = int(report["min_matured_observations"])

    criteria = {
        "minimum_matured_observations": matured >= required,
        "average_net_return_positive": _criterion(
            candidate.get("average_net_return_pct"), 0.0
        ),
        "median_net_return_positive": _criterion(
            candidate.get("median_net_return_pct"), 0.0
        ),
        "positive_return_rate_above_50": _criterion(
            candidate.get("positive_return_rate_pct"), MIN_POSITIVE_RATE_PCT
        ),
        "uplift_vs_baseline_positive": _criterion(
            report.get("uplift_vs_baseline_pct_points"), 0.0
        ),
        "historical_integrity_valid": True,
        "frozen_experiment_valid": True,
    }

    metric_keys = (
        "average_net_return_positive",
        "median_net_return_positive",
        "positive_return_rate_above_50",
        "uplift_vs_baseline_positive",
    )

    if matured < required:
        decision = "NOT_READY"
        reason = (
            f"Prospective sample is incomplete: {matured} of {required} "
            "matured candidate observations."
        )
    elif any(criteria[key] is None for key in metric_keys):
        decision = "INCONCLUSIVE"
        reason = (
            "Minimum sample reached, but one or more required prospective metrics "
            "are unavailable."
        )
    elif all(bool(criteria[key]) for key in metric_keys):
        decision = "PASS_RESEARCH"
        reason = (
            "All pre-registered prospective research criteria are satisfied. "
            "A separate human Phase 6 review is still required."
        )
    else:
        decision = "FAIL_RESEARCH"
        reason = (
            "Minimum sample reached, but at least one pre-registered prospective "
            "research criterion failed."
        )

    frozen = report["candidate"]
    return {
        "phase": "5G.3-prospective-decision-protocol",
        "source_created_at": (report.get("metadata") or {}).get("created_at"),
        "as_of_ms": int(report["as_of_ms"]),
        "decision": decision,
        "reason": reason,
        "research_gate_passed": decision == "PASS_RESEARCH",
        "phase6_eligible": False,
        "phase6_blocked": True,
        "criteria": criteria,
        "thresholds": {
            "min_matured_candidate_observations": required,
            "average_net_return_pct": "> 0",
            "median_net_return_pct": "> 0",
            "positive_return_rate_pct": "> 50",
            "uplift_vs_baseline_pct_points": "> 0",
        },
        "observed": {
            "candidate_matured": matured,
            "candidate_average_net_return_pct": candidate.get(
                "average_net_return_pct"
            ),
            "candidate_median_net_return_pct": candidate.get(
                "median_net_return_pct"
            ),
            "candidate_positive_return_rate_pct": candidate.get(
                "positive_return_rate_pct"
            ),
            "baseline_average_net_return_pct": baseline.get(
                "average_net_return_pct"
            ),
            "uplift_vs_baseline_pct_points": report.get(
                "uplift_vs_baseline_pct_points"
            ),
        },
        "frozen_experiment": {
            "symbol": frozen["symbol"],
            "feature": frozen["feature"],
            "operator": frozen["operator"],
            "value": frozen["value"],
            "frozen_at_ms": int(report["frozen_at_ms"]),
            "outcome_hours": int(report["outcome_hours"]),
        },
        "guardrails": {
            "automatic_phase6_promotion": False,
            "execution_enabled": False,
            "strategy_changes_allowed": False,
            "private_binance_api": False,
        },
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5G.3 pre-registered prospective decision protocol"
    )
    parser.add_argument("--input", default="reports/phase5g/latest.json")
    parser.add_argument("--output", default="reports/phase5g/decision.json")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report = json.loads(Path(args.input).read_text(encoding="utf-8"))
    decision = build_decision(report)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(decision, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    print(
        f"{decision['decision']} | candidate matured "
        f"{decision['observed']['candidate_matured']}/"
        f"{decision['thresholds']['min_matured_candidate_observations']}"
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
