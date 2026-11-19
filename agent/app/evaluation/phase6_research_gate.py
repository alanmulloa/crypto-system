from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ResearchGateSnapshot:
    experiment_id: str
    research_decision: str | None
    research_gate_passed: bool
    sample_ready: bool
    phase6_blocked: bool
    eligible_for_readiness_review: bool
    detail: str


def build_research_gate_snapshot(
    *,
    experiment_id: str,
    decision: Mapping[str, Any] | None,
    review: Mapping[str, Any] | None,
) -> ResearchGateSnapshot:
    observed = (
        str(decision.get("decision"))
        if decision and decision.get("decision") is not None
        else None
    )
    research_passed = bool(
        decision
        and decision.get("research_gate_passed") is True
        and observed == "PASS_RESEARCH"
    )
    sample_ready = bool(review and review.get("sample_ready") is True)
    eligible = research_passed and sample_ready

    if eligible:
        detail = (
            "Research evidence passed its prospective gate. "
            "Phase 6 remains blocked pending separate readiness and human approval."
        )
    elif observed == "FAIL_RESEARCH":
        detail = "Prospective research failed; Phase 6 readiness is not permitted."
    elif observed == "INCONCLUSIVE":
        detail = "Prospective research is inconclusive; more human research review is required."
    else:
        detail = "Prospective research is not ready for Phase 6 review."

    return ResearchGateSnapshot(
        experiment_id=experiment_id,
        research_decision=observed,
        research_gate_passed=research_passed,
        sample_ready=sample_ready,
        phase6_blocked=True,
        eligible_for_readiness_review=eligible,
        detail=detail,
    )


def research_gate_to_dict(value: ResearchGateSnapshot) -> dict[str, Any]:
    return asdict(value)
