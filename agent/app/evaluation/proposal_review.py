from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.evaluation.experiment_registry import ExperimentRegistry


MIN_VALIDATION_UPLIFT_PCT_POINTS = 0.10


@dataclass(frozen=True)
class ProposalReview:
    proposal_id: str
    symbol: str
    strategy: str
    direction: str
    feature: str
    operator: str
    threshold: float | int | str
    validation_uplift_pct_points: float
    decision: str
    reason: str
    matched_experiment_id: str | None = None
    research_only: bool = True
    auto_register: bool = False
    auto_freeze: bool = False
    phase6_blocked: bool = True


def _same_rule(proposal: Mapping[str, Any], experiment: Any) -> bool:
    return (
        str(proposal["symbol"]) == experiment.symbol
        and str(proposal["strategy"]) == experiment.strategy
        and str(proposal["direction"]) == experiment.direction
        and str(proposal["feature"]) == experiment.feature
        and str(proposal["operator"]) == experiment.operator
        and proposal["threshold"] == experiment.threshold
        and int(proposal["outcome_hours"]) == experiment.outcome_hours
    )


def _same_research_family(proposal: Mapping[str, Any], experiment: Any) -> bool:
    return (
        str(proposal["symbol"]) == experiment.symbol
        and str(proposal["strategy"]) == experiment.strategy
        and str(proposal["direction"]) == experiment.direction
        and str(proposal["feature"]) == experiment.feature
    )


def review_proposal(
    proposal: Mapping[str, Any],
    registry: ExperimentRegistry,
) -> ProposalReview:
    required = {
        "id",
        "symbol",
        "strategy",
        "direction",
        "feature",
        "operator",
        "threshold",
        "outcome_hours",
        "validation_uplift_pct_points",
    }
    missing = sorted(required - set(proposal))
    if missing:
        raise ValueError(f"proposal missing required fields: {missing}")

    exact = next(
        (
            experiment
            for experiment in registry.experiments
            if _same_rule(proposal, experiment)
        ),
        None,
    )
    if exact is not None:
        return ProposalReview(
            proposal_id=str(proposal["id"]),
            symbol=str(proposal["symbol"]),
            strategy=str(proposal["strategy"]),
            direction=str(proposal["direction"]),
            feature=str(proposal["feature"]),
            operator=str(proposal["operator"]),
            threshold=proposal["threshold"],
            validation_uplift_pct_points=float(
                proposal["validation_uplift_pct_points"]
            ),
            decision="ALREADY_TRACKED",
            reason="An exact experiment definition is already present in the registry.",
            matched_experiment_id=exact.id,
        )

    overlapping = next(
        (
            experiment
            for experiment in registry.experiments
            if _same_research_family(proposal, experiment)
        ),
        None,
    )
    if overlapping is not None:
        return ProposalReview(
            proposal_id=str(proposal["id"]),
            symbol=str(proposal["symbol"]),
            strategy=str(proposal["strategy"]),
            direction=str(proposal["direction"]),
            feature=str(proposal["feature"]),
            operator=str(proposal["operator"]),
            threshold=proposal["threshold"],
            validation_uplift_pct_points=float(
                proposal["validation_uplift_pct_points"]
            ),
            decision="HUMAN_REVIEW",
            reason=(
                "A related experiment for the same symbol/strategy/direction/feature "
                "already exists with a different rule."
            ),
            matched_experiment_id=overlapping.id,
        )

    uplift = float(proposal["validation_uplift_pct_points"])
    if uplift < MIN_VALIDATION_UPLIFT_PCT_POINTS:
        return ProposalReview(
            proposal_id=str(proposal["id"]),
            symbol=str(proposal["symbol"]),
            strategy=str(proposal["strategy"]),
            direction=str(proposal["direction"]),
            feature=str(proposal["feature"]),
            operator=str(proposal["operator"]),
            threshold=proposal["threshold"],
            validation_uplift_pct_points=uplift,
            decision="REJECT_WEAK_VALIDATION",
            reason=(
                "Validation uplift is below the pre-registered minimum of "
                f"{MIN_VALIDATION_UPLIFT_PCT_POINTS:.2f} percentage points."
            ),
        )

    return ProposalReview(
        proposal_id=str(proposal["id"]),
        symbol=str(proposal["symbol"]),
        strategy=str(proposal["strategy"]),
        direction=str(proposal["direction"]),
        feature=str(proposal["feature"]),
        operator=str(proposal["operator"]),
        threshold=proposal["threshold"],
        validation_uplift_pct_points=uplift,
        decision="READY_TO_REGISTER",
        reason=(
            "Proposal is not already tracked and meets the pre-registered "
            "minimum validation uplift."
        ),
    )


def review_discovery_payload(
    payload: Mapping[str, Any],
    registry: ExperimentRegistry,
) -> tuple[ProposalReview, ...]:
    metadata = payload.get("metadata") or {}
    if metadata.get("phase") != "5H.4":
        raise ValueError("proposal review requires a Phase 5H.4 artifact")
    if metadata.get("research_only") is not True:
        raise ValueError("Phase 5H.4 artifact must be research_only")
    if metadata.get("auto_register") is not False:
        raise ValueError("Phase 5H.4 artifact must have auto_register=false")
    if metadata.get("auto_freeze") is not False:
        raise ValueError("Phase 5H.4 artifact must have auto_freeze=false")

    return tuple(
        review_proposal(proposal, registry)
        for proposal in payload.get("proposals") or []
    )
