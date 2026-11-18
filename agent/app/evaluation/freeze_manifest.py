from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from app.evaluation.experiment_registry import (
    ExperimentStatus,
    ResearchExperiment,
    experiment_definition_snapshot,
)
from app.evaluation.freeze_review import review_freeze_readiness


def canonical_json_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def freeze_definition(experiment: ResearchExperiment) -> dict[str, Any]:
    definition = experiment_definition_snapshot(experiment)
    definition.pop("freeze_at_ms", None)
    return definition


@dataclass(frozen=True)
class ArtifactReference:
    path: str
    sha256: str
    decision: str


def build_freeze_manifest(
    *,
    experiment: ResearchExperiment,
    calibration_artifact: Mapping[str, Any],
    validation_artifact: Mapping[str, Any],
    freeze_review_artifact: Mapping[str, Any],
    calibration_path: str,
    validation_path: str,
    freeze_review_path: str,
    created_at: str,
) -> dict[str, Any]:
    if experiment.status is not ExperimentStatus.VALIDATION:
        raise ValueError("freeze manifest requires experiment status VALIDATION")
    if experiment.freeze_at_ms is not None:
        raise ValueError("freeze manifest requires freeze_at_ms to be null")

    review_meta = freeze_review_artifact.get("metadata") or {}
    review = freeze_review_artifact.get("review") or {}
    if review_meta.get("phase") != "5H.8":
        raise ValueError("freeze review artifact must be Phase 5H.8")
    if str(review_meta.get("experiment_id")) != experiment.id:
        raise ValueError("freeze review experiment_id mismatch")
    if review_meta.get("research_only") is not True:
        raise ValueError("freeze review must be research_only")
    if review_meta.get("auto_freeze") is not False:
        raise ValueError("freeze review must have auto_freeze=false")
    if review_meta.get("phase6_blocked") is not True:
        raise ValueError("freeze review must keep phase6_blocked=true")
    if review.get("decision") != "READY_FOR_FREEZE":
        raise ValueError("freeze review decision must be READY_FOR_FREEZE")

    recomputed = review_freeze_readiness(
        experiment=experiment,
        calibration_artifact=calibration_artifact,
        validation_artifact=validation_artifact,
    )
    if recomputed.decision != "READY_FOR_FREEZE":
        raise ValueError(
            "calibration/validation artifacts no longer satisfy freeze readiness"
        )

    cal_decision = str(calibration_artifact["review"]["decision"])
    val_decision = str(validation_artifact["review"]["decision"])
    definition = freeze_definition(experiment)
    definition_fingerprint = canonical_json_sha256(definition)

    cal_ref = ArtifactReference(
        path=calibration_path,
        sha256=canonical_json_sha256(calibration_artifact),
        decision=cal_decision,
    )
    val_ref = ArtifactReference(
        path=validation_path,
        sha256=canonical_json_sha256(validation_artifact),
        decision=val_decision,
    )
    freeze_ref = ArtifactReference(
        path=freeze_review_path,
        sha256=canonical_json_sha256(freeze_review_artifact),
        decision=str(review["decision"]),
    )

    return {
        "schema_version": 1,
        "metadata": {
            "phase": "5H.9",
            "created_at": created_at,
            "research_only": True,
            "auto_transition": False,
            "auto_freeze": False,
            "phase6_blocked": True,
        },
        "experiment_id": experiment.id,
        "frozen_definition": definition,
        "definition_fingerprint_sha256": definition_fingerprint,
        "freeze_at_ms": None,
        "freeze_timestamp_pending": True,
        "calibration": cal_ref.__dict__,
        "validation": val_ref.__dict__,
        "freeze_review": freeze_ref.__dict__,
        "calibration_decision": cal_decision,
        "validation_decision": val_decision,
        "outcome_hours": experiment.outcome_hours,
        "fee_bps": experiment.fee_bps,
        "slippage_bps": experiment.slippage_bps,
    }
