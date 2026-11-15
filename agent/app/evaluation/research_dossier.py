from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.evaluation.experiment_registry import (
    ExperimentRegistry,
    ExperimentStatus,
)
from app.evaluation.research_experiment_planner import (
    LEGACY_PHASE5G_EXPERIMENT_ID,
)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _next_action(status: ExperimentStatus, decision: str | None) -> str:
    if status is ExperimentStatus.DRAFT:
        return "START_CALIBRATION_WHEN_EXPLICITLY_APPROVED"
    if status is ExperimentStatus.CALIBRATION:
        return "RUN_CALIBRATION_HARNESS"
    if status is ExperimentStatus.VALIDATION:
        return "RUN_VALIDATION_HARNESS"
    if status is ExperimentStatus.FROZEN:
        return "GENERATE_OR_VERIFY_PROSPECTIVE_BOOTSTRAP"
    if status is ExperimentStatus.PROSPECTIVE:
        if decision == "PASS_RESEARCH":
            return "HUMAN_PHASE6_REVIEW_REQUIRED"
        if decision == "FAIL_RESEARCH":
            return "HUMAN_RESEARCH_REVIEW_REQUIRED"
        return "CONTINUE_PROSPECTIVE_COLLECTION"
    if status is ExperimentStatus.COMPLETE:
        return "NO_ACTION"
    return "NO_ACTION_REJECTED"


def build_research_dossier(
    *,
    registry: ExperimentRegistry,
    reports_root: Path,
    phase5g_root: Path,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for experiment in sorted(registry.experiments, key=lambda item: item.id):
        if experiment.id == LEGACY_PHASE5G_EXPERIMENT_ID:
            review = _read_json(phase5g_root / "review.json")
            decision_payload = _read_json(phase5g_root / "decision.json")
            pipeline = "PHASE5G_LEGACY"
        else:
            root = reports_root / experiment.id
            review = _read_json(root / "review.json")
            decision_payload = _read_json(root / "decision.json")
            pipeline = "GENERIC_5H"

        observed_decision = (
            decision_payload.get("decision")
            if decision_payload is not None
            else experiment.decision
        )
        progress = (
            review.get("progress")
            if review is not None
            else None
        )
        rows.append(
            {
                "experiment_id": experiment.id,
                "symbol": experiment.symbol,
                "strategy": experiment.strategy,
                "status": experiment.status.value,
                "pipeline": pipeline,
                "research_decision": observed_decision,
                "progress": progress,
                "next_allowed_action": _next_action(
                    experiment.status,
                    observed_decision,
                ),
                "phase6_eligible": False,
                "phase6_blocked": True,
            }
        )

    return {
        "phase": "5H.17",
        "research_only": True,
        "phase6_blocked": True,
        "automatic_phase6_promotion": False,
        "experiments": rows,
    }
