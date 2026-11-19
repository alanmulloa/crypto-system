from __future__ import annotations

from dataclasses import asdict, dataclass

from app.evaluation.experiment_registry import (
    ExperimentRegistry,
    ExperimentStatus,
)


LEGACY_PHASE5G_EXPERIMENT_ID = "phase5g-xrp-low-volume-1h"


@dataclass(frozen=True)
class ResearchPlanItem:
    experiment_id: str
    status: str
    pipeline: str
    next_action: str
    automatic_transition: bool = False
    phase6_blocked: bool = True


def plan_registry(registry: ExperimentRegistry) -> tuple[ResearchPlanItem, ...]:
    result: list[ResearchPlanItem] = []
    for experiment in sorted(registry.experiments, key=lambda item: item.id):
        if experiment.id == LEGACY_PHASE5G_EXPERIMENT_ID:
            pipeline = "PHASE5G_LEGACY"
            action = "CONTINUE_EXISTING_PHASE5G"
        elif experiment.status is ExperimentStatus.FROZEN:
            pipeline = "GENERIC_5H"
            action = "BOOTSTRAP_REQUIRED"
        elif experiment.status is ExperimentStatus.PROSPECTIVE:
            pipeline = "GENERIC_5H"
            action = "COLLECT_PROSPECTIVE_EVIDENCE"
        else:
            pipeline = "RESEARCH_LIFECYCLE"
            action = "NO_PROSPECTIVE_ACTION"

        result.append(
            ResearchPlanItem(
                experiment_id=experiment.id,
                status=experiment.status.value,
                pipeline=pipeline,
                next_action=action,
            )
        )
    return tuple(result)


def plan_to_dict(registry: ExperimentRegistry) -> dict:
    items = plan_registry(registry)
    return {
        "phase": "5H.14",
        "phase6_blocked": True,
        "automatic_transitions": False,
        "experiments": [asdict(item) for item in items],
    }
