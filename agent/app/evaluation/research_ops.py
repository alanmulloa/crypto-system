from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.evaluation.experiment_registry import ExperimentRegistry, ExperimentStatus
from app.evaluation.research_experiment_planner import (
    LEGACY_PHASE5G_EXPERIMENT_ID,
)
from app.evaluation.research_health import build_research_health, health_to_dict


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_research_ops_report(
    *,
    registry: ExperimentRegistry,
    phase5g_root: Path,
    generic_root: Path,
    as_of: datetime,
    max_age_hours: float = 12.0,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    as_of_utc = as_of.astimezone(timezone.utc)
    as_of_ms = int(as_of_utc.timestamp() * 1000)

    for experiment in sorted(registry.experiments, key=lambda item: item.id):
        if experiment.status is not ExperimentStatus.PROSPECTIVE:
            rows.append(
                {
                    "experiment_id": experiment.id,
                    "status": experiment.status.value,
                    "pipeline": "RESEARCH_LIFECYCLE",
                    "health_state": "NOT_PROSPECTIVE",
                    "recommended_action": "FOLLOW_LIFECYCLE_GATE",
                    "phase6_blocked": True,
                }
            )
            continue

        if experiment.id == LEGACY_PHASE5G_EXPERIMENT_ID:
            root = phase5g_root
            pipeline = "PHASE5G_LEGACY"
        else:
            root = generic_root / experiment.id
            pipeline = "GENERIC_5H"

        latest = _read_json(root / "latest.json")
        decision = _read_json(root / "decision.json")
        if experiment.freeze_at_ms is None:
            raise ValueError("prospective experiment requires freeze_at_ms")

        health = build_research_health(
            latest=latest,
            decision=decision,
            frozen_at_ms=experiment.freeze_at_ms,
            as_of_ms=as_of_ms,
            as_of=as_of_utc,
            max_age_hours=max_age_hours,
        )
        rows.append(
            {
                "experiment_id": experiment.id,
                "symbol": experiment.symbol,
                "status": experiment.status.value,
                "pipeline": pipeline,
                **health_to_dict(health),
            }
        )

    attention = [
        row
        for row in rows
        if str(row.get("health_state") or row.get("state", "")).startswith(
            "ATTENTION"
        )
    ]
    return {
        "phase": "5I.4",
        "generated_at": as_of_utc.isoformat(),
        "research_only": True,
        "phase6_blocked": True,
        "automatic_lifecycle_transition": False,
        "automatic_strategy_change": False,
        "attention_count": len(attention),
        "experiments": rows,
    }
