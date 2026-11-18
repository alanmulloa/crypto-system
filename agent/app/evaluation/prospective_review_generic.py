from __future__ import annotations

from typing import Any, Mapping

from app.evaluation.prospective_bootstrap import (
    GenericProspectiveProtocol,
    validate_generic_report,
)


def _cohort_metrics(summary: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "observations": int(summary.get("observations", 0)),
        "pending": int(summary.get("pending", 0)),
        "matured": int(summary.get("matured", 0)),
        "average_net_return_pct": summary.get("average_net_return_pct"),
        "median_net_return_pct": summary.get("median_net_return_pct"),
        "positive_return_rate_pct": summary.get("positive_return_rate_pct"),
    }


def build_generic_review(
    report: Mapping[str, Any],
    *,
    protocol: GenericProspectiveProtocol,
) -> dict[str, Any]:
    validate_generic_report(report, protocol=protocol)

    baseline = _cohort_metrics(report.get("baseline") or {})
    candidate = _cohort_metrics(report.get("candidate_summary") or {})
    minimum = protocol.min_matured_observations
    matured = candidate["matured"]
    sample_ready = matured >= minimum

    if sample_ready:
        state = "REVIEW_REQUIRED"
        decision = "REVIEW"
        reason = (
            "Minimum matured candidate sample reached; formal human research "
            "review is required."
        )
    elif candidate["observations"] == 0:
        state = "WAITING_FOR_CANDIDATE_SIGNAL"
        decision = "WAIT"
        reason = "No qualifying frozen-candidate observation has been recorded."
    elif candidate["matured"] == 0:
        state = "WAITING_FOR_MATURITY"
        decision = "WAIT"
        reason = (
            "Candidate observations exist but none has a complete configured "
            "outcome yet."
        )
    else:
        state = "ACCUMULATING_MATURED_SAMPLE"
        decision = "WAIT"
        reason = (
            f"{matured} of {minimum} matured candidate observations collected."
        )

    progress_pct = min(100.0, matured / minimum * 100.0)
    return {
        "phase": "5H.11-generic-monitoring-review",
        "source_created_at": (report.get("metadata") or {}).get("created_at"),
        "decision": decision,
        "state": state,
        "reason": reason,
        "sample_ready": sample_ready,
        "phase6_blocked": True,
        "phase6_eligible": False,
        "progress": {
            "matured_candidate_observations": matured,
            "required_matured_candidate_observations": minimum,
            "percent": progress_pct,
            "remaining": max(0, minimum - matured),
        },
        "baseline": baseline,
        "candidate": candidate,
        "uplift_vs_baseline_pct_points": report.get(
            "uplift_vs_baseline_pct_points"
        ),
        "frozen_experiment": report["frozen_experiment"],
        "guardrails": {
            "automatic_promotion": False,
            "automatic_phase6_promotion": False,
            "execution_enabled": False,
            "testnet_enabled": False,
        },
    }
