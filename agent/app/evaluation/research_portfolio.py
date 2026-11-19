from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from app.evaluation.experiment_registry import ExperimentRegistry, ExperimentStatus
from app.evaluation.proposal_review import review_proposal


MAX_NEW_CONCURRENT_EXPERIMENTS = 2
MAX_NEW_PER_SYMBOL = 1
MAX_NEW_PER_FEATURE = 1

_ACTIVE = {
    ExperimentStatus.DRAFT,
    ExperimentStatus.CALIBRATION,
    ExperimentStatus.VALIDATION,
    ExperimentStatus.FROZEN,
    ExperimentStatus.PROSPECTIVE,
}


@dataclass(frozen=True)
class ResearchQueueItem:
    proposal_id: str
    symbol: str
    feature: str
    decision: str
    reason: str
    priority: int | None
    human_registration_required: bool
    auto_register: bool = False
    phase6_blocked: bool = True


def _active_new_count(registry: ExperimentRegistry) -> int:
    return sum(
        experiment.status in _ACTIVE
        and experiment.id != "phase5g-xrp-low-volume-1h"
        for experiment in registry.experiments
    )


def build_promotion_queue(
    *,
    proposals: Sequence[Mapping[str, Any]],
    registry: ExperimentRegistry,
    max_new_concurrent: int = MAX_NEW_CONCURRENT_EXPERIMENTS,
) -> tuple[ResearchQueueItem, ...]:
    capacity = max(0, max_new_concurrent - _active_new_count(registry))
    queued: list[ResearchQueueItem] = []
    used_symbols: set[str] = set()
    used_features: set[str] = set()
    priority = 0

    for proposal in proposals:
        review = review_proposal(proposal, registry)
        if review.decision != "READY_TO_REGISTER":
            queued.append(
                ResearchQueueItem(
                    proposal_id=review.proposal_id,
                    symbol=review.symbol,
                    feature=review.feature,
                    decision=review.decision,
                    reason=review.reason,
                    priority=None,
                    human_registration_required=False,
                )
            )
            continue

        if capacity <= 0:
            decision = "DEFER_RESEARCH_BUDGET"
            reason = "Maximum concurrent new research experiments reached."
            item_priority = None
        elif review.symbol in used_symbols:
            decision = "DEFER_SYMBOL_DIVERSITY"
            reason = "Another queued proposal already uses this symbol."
            item_priority = None
        elif review.feature in used_features:
            decision = "DEFER_FEATURE_DIVERSITY"
            reason = "Another queued proposal already uses this feature."
            item_priority = None
        else:
            priority += 1
            capacity -= 1
            used_symbols.add(review.symbol)
            used_features.add(review.feature)
            decision = "READY_FOR_HUMAN_REGISTRATION"
            reason = (
                "Proposal passed review and research portfolio constraints. "
                "Explicit human registration as DRAFT is still required."
            )
            item_priority = priority

        queued.append(
            ResearchQueueItem(
                proposal_id=review.proposal_id,
                symbol=review.symbol,
                feature=review.feature,
                decision=decision,
                reason=reason,
                priority=item_priority,
                human_registration_required=(
                    decision == "READY_FOR_HUMAN_REGISTRATION"
                ),
            )
        )

    return tuple(queued)


def queue_to_dict(items: Sequence[ResearchQueueItem]) -> dict[str, Any]:
    return {
        "phase": "5K.5",
        "research_only": True,
        "auto_register": False,
        "automatic_lifecycle_transition": False,
        "phase6_blocked": True,
        "queue": [asdict(item) for item in items],
    }
