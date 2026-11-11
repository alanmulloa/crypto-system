from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from app.evaluation.experiment_registry import (
    ExperimentStatus,
    ResearchExperiment,
)


_WORKSPACE_ALLOWED_STATUSES = {
    ExperimentStatus.DRAFT,
    ExperimentStatus.CALIBRATION,
    ExperimentStatus.VALIDATION,
}

_DEFINITION_FIELDS = (
    "symbol",
    "strategy",
    "direction",
    "feature",
    "operator",
    "threshold",
    "calibration_period",
    "validation_period",
    "freeze_at_ms",
    "outcome_hours",
    "fee_bps",
    "slippage_bps",
)


def definition_snapshot(experiment: ResearchExperiment) -> dict[str, Any]:
    payload = experiment.to_dict()
    return {field: payload[field] for field in _DEFINITION_FIELDS}


@dataclass(frozen=True)
class CandidateResearchWorkspace:
    experiment_id: str
    definition: Mapping[str, Any]
    research_only: bool = True
    phase6_blocked: bool = True
    workspace_kind: str = "candidate-research"

    def __post_init__(self) -> None:
        if not self.experiment_id.strip():
            raise ValueError("experiment_id is required")
        missing = sorted(set(_DEFINITION_FIELDS) - set(self.definition))
        if missing:
            raise ValueError(f"workspace definition is incomplete: {missing}")
        if self.research_only is not True:
            raise ValueError("candidate workspaces must remain research_only")
        if self.phase6_blocked is not True:
            raise ValueError("candidate workspaces cannot unblock Phase 6")
        if self.workspace_kind != "candidate-research":
            raise ValueError("unsupported workspace_kind")

    @classmethod
    def from_experiment(
        cls,
        experiment: ResearchExperiment,
    ) -> "CandidateResearchWorkspace":
        if experiment.status not in _WORKSPACE_ALLOWED_STATUSES:
            raise ValueError(
                f"workspace not allowed for experiment status: {experiment.status.value}"
            )
        return cls(
            experiment_id=experiment.id,
            definition=definition_snapshot(experiment),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CandidateResearchWorkspace":
        required = {
            "schema_version",
            "experiment_id",
            "definition",
            "research_only",
            "phase6_blocked",
            "workspace_kind",
        }
        missing = sorted(required - set(payload))
        if missing:
            raise ValueError(f"missing workspace fields: {missing}")
        if int(payload["schema_version"]) != 1:
            raise ValueError("unsupported workspace schema_version")
        definition = payload["definition"]
        if not isinstance(definition, Mapping):
            raise ValueError("workspace definition must be an object")
        return cls(
            experiment_id=str(payload["experiment_id"]),
            definition=dict(definition),
            research_only=bool(payload["research_only"]),
            phase6_blocked=bool(payload["phase6_blocked"]),
            workspace_kind=str(payload["workspace_kind"]),
        )

    @classmethod
    def load(cls, path: Path) -> "CandidateResearchWorkspace":
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "experiment_id": self.experiment_id,
            "workspace_kind": self.workspace_kind,
            "research_only": self.research_only,
            "phase6_blocked": self.phase6_blocked,
            "definition": dict(self.definition),
        }

    def serialize(self) -> str:
        return json.dumps(
            self.to_dict(),
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ) + "\n"

    def validate_against(self, experiment: ResearchExperiment) -> None:
        if experiment.id != self.experiment_id:
            raise ValueError(
                f"workspace experiment mismatch: {self.experiment_id} != {experiment.id}"
            )
        if experiment.status not in _WORKSPACE_ALLOWED_STATUSES:
            raise ValueError(
                f"workspace no longer allowed for experiment status: "
                f"{experiment.status.value}"
            )
        current = definition_snapshot(experiment)
        changed = [
            field
            for field in _DEFINITION_FIELDS
            if self.definition[field] != current[field]
        ]
        if changed:
            raise ValueError(
                "workspace definition diverged from registry: " + ", ".join(changed)
            )


def initialize_workspace(
    *,
    experiment: ResearchExperiment,
    workspace_root: Path,
) -> Path:
    workspace = CandidateResearchWorkspace.from_experiment(experiment)
    directory = workspace_root / experiment.id
    manifest = directory / "workspace.json"

    if manifest.exists():
        existing = CandidateResearchWorkspace.load(manifest)
        if existing.serialize() != workspace.serialize():
            raise ValueError(
                f"workspace already exists with different definition: {manifest}"
            )
        existing.validate_against(experiment)
        return manifest

    directory.mkdir(parents=True, exist_ok=True)
    (directory / "artifacts").mkdir(exist_ok=True)
    (directory / "notes").mkdir(exist_ok=True)
    manifest.write_text(workspace.serialize(), encoding="utf-8")
    return manifest
