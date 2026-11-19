from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.evaluation.phase6_approval import HumanApproval
from app.evaluation.phase6_execution_boundary import ExecutionBoundary
from app.evaluation.phase6_research_gate import ResearchGateSnapshot
from app.evaluation.phase6_risk_preflight import RiskPreflight


@dataclass(frozen=True)
class Phase6Readiness:
    state: str
    research_ready: bool
    risk_ready: bool
    human_approval_present: bool
    execution_boundary_safe: bool
    phase6_eligible: bool
    phase6_blocked: bool
    automatic_activation: bool
    next_action: str
    detail: str


def build_phase6_readiness(
    *,
    research: ResearchGateSnapshot,
    risk: RiskPreflight,
    boundary: ExecutionBoundary,
    approval: HumanApproval,
) -> Phase6Readiness:
    if approval.experiment_id != research.experiment_id:
        raise ValueError("approval experiment_id mismatch")

    boundary_safe = (
        boundary.spot_only
        and not boundary.futures_allowed
        and not boundary.margin_allowed
        and not boundary.leverage_allowed
        and not boundary.withdrawals_allowed
        and not boundary.live_orders_allowed
        and not boundary.testnet_orders_allowed
        and not boundary.private_api_use_allowed
        and not boundary.automatic_activation_allowed
    )
    research_ready = research.eligible_for_readiness_review
    risk_ready = risk.safe_for_readiness_review
    approved = approval.approved and approval.allows_testnet_preparation

    if not research_ready:
        state = "BLOCKED_RESEARCH"
        action = "CONTINUE_OR_REVIEW_PROSPECTIVE_RESEARCH"
        detail = "Prospective research has not passed the evidence gate."
    elif not risk_ready:
        state = "BLOCKED_RISK_PREFLIGHT"
        action = "FIX_RUNTIME_SAFETY_SETTINGS"
        detail = "Runtime risk settings are not ready for Phase 6 preparation."
    elif not boundary_safe:
        state = "BLOCKED_EXECUTION_BOUNDARY"
        action = "RESTORE_EXECUTION_GUARDRAILS"
        detail = "Execution boundary is not sufficiently restrictive."
    elif not approved:
        state = "READY_FOR_HUMAN_APPROVAL"
        action = "OBTAIN_EXPLICIT_TESTNET_PREPARATION_APPROVAL"
        detail = (
            "Research and risk checks passed. Explicit human approval is still required."
        )
    else:
        state = "APPROVED_FOR_TESTNET_PREPARATION"
        action = "GENERATE_TESTNET_DRY_RUN_PLAN"
        detail = (
            "Human approval covers preparation only. Testnet orders remain disabled."
        )

    return Phase6Readiness(
        state=state,
        research_ready=research_ready,
        risk_ready=risk_ready,
        human_approval_present=approved,
        execution_boundary_safe=boundary_safe,
        phase6_eligible=False,
        phase6_blocked=True,
        automatic_activation=False,
        next_action=action,
        detail=detail,
    )


def readiness_to_dict(value: Phase6Readiness) -> dict[str, Any]:
    return asdict(value)
