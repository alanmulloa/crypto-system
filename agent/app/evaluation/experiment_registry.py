from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence


class ExperimentStatus(str, Enum):
    DRAFT = "DRAFT"
    CALIBRATION = "CALIBRATION"
    VALIDATION = "VALIDATION"
    REJECTED = "REJECTED"
    FROZEN = "FROZEN"
    PROSPECTIVE = "PROSPECTIVE"
    COMPLETE = "COMPLETE"


_ALLOWED_TRANSITIONS = {
    ExperimentStatus.DRAFT: {
        ExperimentStatus.CALIBRATION,
        ExperimentStatus.REJECTED,
    },
    ExperimentStatus.CALIBRATION: {
        ExperimentStatus.VALIDATION,
        ExperimentStatus.REJECTED,
    },
    ExperimentStatus.VALIDATION: {
        ExperimentStatus.FROZEN,
        ExperimentStatus.REJECTED,
    },
    ExperimentStatus.FROZEN: {
        ExperimentStatus.PROSPECTIVE,
        ExperimentStatus.REJECTED,
    },
    ExperimentStatus.PROSPECTIVE: {
        ExperimentStatus.COMPLETE,
        ExperimentStatus.REJECTED,
    },
    ExperimentStatus.REJECTED: set(),
    ExperimentStatus.COMPLETE: set(),
}

_LOCKED_STATUSES = {
    ExperimentStatus.FROZEN,
    ExperimentStatus.PROSPECTIVE,
    ExperimentStatus.COMPLETE,
}

_IMMUTABLE_DEFINITION_FIELDS = (
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


@dataclass(frozen=True)
class ResearchExperiment:
    id: str
    symbol: str
    strategy: str
    direction: str
    feature: str
    operator: str
    threshold: float | str
    calibration_period: str | None
    validation_period: str | None
    freeze_at_ms: int | None
    outcome_hours: int
    fee_bps: float
    slippage_bps: float
    status: ExperimentStatus
    decision: str | None
    artifact_path: str

    def __post_init__(self) -> None:
        for field_name in (
            "id",
            "symbol",
            "strategy",
            "direction",
            "feature",
            "operator",
            "artifact_path",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} is required")

        if isinstance(self.threshold, str) and not self.threshold.strip():
            raise ValueError("threshold cannot be empty")
        if self.threshold is None:
            raise ValueError("threshold is required")
        if self.outcome_hours <= 0:
            raise ValueError("outcome_hours must be positive")
        if self.fee_bps < 0 or self.slippage_bps < 0:
            raise ValueError("fee_bps and slippage_bps cannot be negative")
        if self.freeze_at_ms is not None and self.freeze_at_ms < 0:
            raise ValueError("freeze_at_ms cannot be negative")
        if self.status in _LOCKED_STATUSES and self.freeze_at_ms is None:
            raise ValueError(f"freeze_at_ms is required for {self.status.value}")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResearchExperiment":
        required = {
            "id",
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
            "status",
            "decision",
            "artifact_path",
        }
        missing = sorted(required - set(payload))
        if missing:
            raise ValueError(f"missing experiment fields: {missing}")
        try:
            status = ExperimentStatus(str(payload["status"]))
        except ValueError as exc:
            raise ValueError(f"invalid experiment status: {payload['status']}") from exc

        return cls(
            id=str(payload["id"]),
            symbol=str(payload["symbol"]),
            strategy=str(payload["strategy"]),
            direction=str(payload["direction"]),
            feature=str(payload["feature"]),
            operator=str(payload["operator"]),
            threshold=payload["threshold"],
            calibration_period=payload["calibration_period"],
            validation_period=payload["validation_period"],
            freeze_at_ms=payload["freeze_at_ms"],
            outcome_hours=int(payload["outcome_hours"]),
            fee_bps=float(payload["fee_bps"]),
            slippage_bps=float(payload["slippage_bps"]),
            status=status,
            decision=payload["decision"],
            artifact_path=str(payload["artifact_path"]),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload

    def transition(
        self,
        new_status: ExperimentStatus,
        *,
        decision: str | None = None,
        **definition_changes: Any,
    ) -> "ResearchExperiment":
        if new_status not in _ALLOWED_TRANSITIONS[self.status]:
            raise ValueError(
                f"invalid experiment status transition: "
                f"{self.status.value} -> {new_status.value}"
            )

        if self.status in _LOCKED_STATUSES:
            changed_locked = [
                field
                for field in _IMMUTABLE_DEFINITION_FIELDS
                if field in definition_changes
                and definition_changes[field] != getattr(self, field)
            ]
            if changed_locked:
                raise ValueError(
                    "frozen experiment definition cannot mutate: "
                    + ", ".join(changed_locked)
                )

        unknown = sorted(set(definition_changes) - set(_IMMUTABLE_DEFINITION_FIELDS))
        if unknown:
            raise ValueError(f"unsupported experiment changes: {unknown}")

        return replace(
            self,
            status=new_status,
            decision=self.decision if decision is None else decision,
            **definition_changes,
        )


@dataclass(frozen=True)
class ExperimentRegistry:
    experiments: tuple[ResearchExperiment, ...]

    def __post_init__(self) -> None:
        ids = [experiment.id for experiment in self.experiments]
        if len(ids) != len(set(ids)):
            raise ValueError("experiment ids must be unique")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ExperimentRegistry":
        raw = payload.get("experiments")
        if not isinstance(raw, list):
            raise ValueError("registry experiments must be a list")
        return cls(tuple(ResearchExperiment.from_dict(item) for item in raw))

    @classmethod
    def load(cls, path: Path) -> "ExperimentRegistry":
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "experiments": [
                experiment.to_dict()
                for experiment in sorted(self.experiments, key=lambda item: item.id)
            ],
        }

    def serialize(self) -> str:
        return json.dumps(
            self.to_dict(),
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ) + "\n"

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.serialize(), encoding="utf-8")

    def get(self, experiment_id: str) -> ResearchExperiment:
        for experiment in self.experiments:
            if experiment.id == experiment_id:
                return experiment
        raise KeyError(experiment_id)

    def add_experiment(
        self,
        experiment: ResearchExperiment,
    ) -> "ExperimentRegistry":
        if experiment.id in {item.id for item in self.experiments}:
            raise ValueError(f"experiment id already exists: {experiment.id}")
        return ExperimentRegistry((*self.experiments, experiment))

    def replace_experiment(
        self,
        experiment: ResearchExperiment,
    ) -> "ExperimentRegistry":
        if experiment.id not in {item.id for item in self.experiments}:
            raise KeyError(experiment.id)
        return ExperimentRegistry(
            tuple(
                experiment if item.id == experiment.id else item
                for item in self.experiments
            )
        )


def experiment_definition_snapshot(
    experiment: ResearchExperiment,
) -> dict[str, Any]:
    return {
        "id": experiment.id,
        "symbol": experiment.symbol,
        "strategy": experiment.strategy,
        "direction": experiment.direction,
        "feature": experiment.feature,
        "operator": experiment.operator,
        "threshold": experiment.threshold,
        "calibration_period": experiment.calibration_period,
        "validation_period": experiment.validation_period,
        "freeze_at_ms": experiment.freeze_at_ms,
        "outcome_hours": experiment.outcome_hours,
        "fee_bps": experiment.fee_bps,
        "slippage_bps": experiment.slippage_bps,
    }


def registry_from_experiments(
    experiments: Sequence[ResearchExperiment],
) -> ExperimentRegistry:
    return ExperimentRegistry(tuple(experiments))
