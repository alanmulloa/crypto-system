from __future__ import annotations

from typing import Any, Mapping

from app.evaluation.prospective_bootstrap import (
    GenericProspectiveProtocol,
    validate_generic_report,
)


MIN_POSITIVE_RATE_PCT = 50.0


def _criterion(
    value: float | None,
    threshold: float,
    *,
    strict: bool = True,
) -> bool | None:
    if value is None:
        return None
    return float(value) > threshold if strict else float(value) >= threshold


def build_generic_decision(
    report: Mapping[str, Any],
    *,
    protocol: GenericProspectiveProtocol,
) -> dict[str, Any]:
    validate_generic_report(report, protocol=protocol)

    candidate = report.get("candidate_summary") or {}
    baseline = report.get("baseline") or {}
    matured = int(candidate.get("matured", 0))
    required = protocol.min_matured_observations

    criteria = {
        "minimum_matured_observations": matured >= required,
        "average_net_return_positive": _criterion(
            candidate.get("average_net_return_pct"),
            0.0,
        ),
        "median_net_return_positive": _criterion(
            candidate.get("median_net_return_pct"),
            0.0,
        ),
        "positive_return_rate_above_50": _criterion(
            candidate.get("positive_return_rate_pct"),
            MIN_POSITIVE_RATE_PCT,
        ),
        "uplift_vs_baseline_positive": _criterion(
            report.get("uplift_vs_baseline_pct_points"),
            0.0,
        ),
        "historical_integrity_valid": True,
        "frozen_definition_valid": True,
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
            f"Prospective sample incomplete: {matured} of {required} "
            "matured candidate observations."
        )
    elif any(criteria[key] is None for key in metric_keys):
        decision = "INCONCLUSIVE"
        reason = (
            "Minimum sample reached, but one or more required metrics "
            "are unavailable."
        )
    elif all(bool(criteria[key]) for key in metric_keys):
        decision = "PASS_RESEARCH"
        reason = (
            "All pre-registered prospective research criteria are satisfied. "
            "Phase 6 remains blocked pending a separate human decision."
        )
    else:
        decision = "FAIL_RESEARCH"
        reason = (
            "Minimum sample reached, but at least one pre-registered "
            "prospective research criterion failed."
        )

    return {
        "phase": "5H.11-generic-prospective-decision",
        "source_created_at": (report.get("metadata") or {}).get("created_at"),
        "decision": decision,
        "reason": reason,
        "research_gate_passed": decision == "PASS_RESEARCH",
        "phase6_eligible": False,
        "phase6_blocked": True,
        "automatic_phase6_promotion": False,
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
        "frozen_experiment": report["frozen_experiment"],
        "guardrails": {
            "execution_enabled": False,
            "testnet_enabled": False,
            "automatic_phase6_promotion": False,
        },
    }
