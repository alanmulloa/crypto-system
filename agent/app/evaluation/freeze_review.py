from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.evaluation.experiment_registry import (
    ExperimentStatus,
    ResearchExperiment,
    experiment_definition_snapshot,
)


@dataclass(frozen=True)
class FreezeReview:
    experiment_id: str
    decision: str
    reason: str
    calibration_integrity_valid: bool
    validation_integrity_valid: bool
    calibration_passed: bool
    validation_passed: bool
    definition_matches: bool
    freeze_at_ms_is_null: bool
    eligible_for_manual_freeze: bool
    auto_transition: bool = False
    auto_freeze: bool = False
    research_only: bool = True
    phase6_blocked: bool = True


def _artifact_integrity(
    artifact: Mapping[str, Any],
    *,
    expected_phase: str,
    experiment: ResearchExperiment,
) -> tuple[bool, bool, str | None]:
    metadata = artifact.get("metadata")
    review = artifact.get("review")
    definition = artifact.get("experiment_definition")
    if not isinstance(metadata, Mapping):
        return False, False, "metadata missing"
    if not isinstance(review, Mapping):
        return False, False, "review missing"
    if not isinstance(definition, Mapping):
        return False, False, "experiment_definition missing"

    if metadata.get("phase") != expected_phase:
        return False, False, "unexpected phase"
    if metadata.get("research_only") is not True:
        return False, False, "research_only guardrail missing"
    if metadata.get("auto_transition") is not False:
        return False, False, "auto_transition guardrail invalid"
    if metadata.get("phase6_blocked") is not True:
        return False, False, "phase6_blocked guardrail invalid"
    if str(metadata.get("experiment_id")) != experiment.id:
        return False, False, "metadata experiment_id mismatch"
    if str(review.get("experiment_id")) != experiment.id:
        return False, False, "review experiment_id mismatch"

    expected = experiment_definition_snapshot(experiment)
    definition_matches = dict(definition) == expected
    return True, definition_matches, None


def review_freeze_readiness(
    *,
    experiment: ResearchExperiment,
    calibration_artifact: Mapping[str, Any],
    validation_artifact: Mapping[str, Any],
) -> FreezeReview:
    cal_integrity, cal_match, cal_error = _artifact_integrity(
        calibration_artifact,
        expected_phase="5H.6",
        experiment=experiment,
    )
    val_integrity, val_match, val_error = _artifact_integrity(
        validation_artifact,
        expected_phase="5H.7",
        experiment=experiment,
    )

    if not cal_integrity or not val_integrity:
        problems = ", ".join(
            item
            for item in (
                f"calibration: {cal_error}" if cal_error else None,
                f"validation: {val_error}" if val_error else None,
            )
            if item is not None
        )
        return FreezeReview(
            experiment_id=experiment.id,
            decision="INCONCLUSIVE",
            reason=f"Artifact integrity could not be established: {problems}.",
            calibration_integrity_valid=cal_integrity,
            validation_integrity_valid=val_integrity,
            calibration_passed=False,
            validation_passed=False,
            definition_matches=False,
            freeze_at_ms_is_null=experiment.freeze_at_ms is None,
            eligible_for_manual_freeze=False,
        )

    cal_review = calibration_artifact["review"]
    val_review = validation_artifact["review"]
    cal_passed = cal_review.get("decision") == "PASS_CALIBRATION"
    val_passed = val_review.get("decision") == "PASS_VALIDATION"
    definition_matches = cal_match and val_match
    freeze_is_null = experiment.freeze_at_ms is None
    correct_status = experiment.status is ExperimentStatus.VALIDATION

    failures: list[str] = []
    if not correct_status:
        failures.append("registry status is not VALIDATION")
    if not cal_passed:
        failures.append("calibration decision is not PASS_CALIBRATION")
    if not val_passed:
        failures.append("validation decision is not PASS_VALIDATION")
    if not definition_matches:
        failures.append("experiment definition drift detected")
    if not freeze_is_null:
        failures.append("freeze_at_ms is already set")

    if failures:
        return FreezeReview(
            experiment_id=experiment.id,
            decision="NOT_READY_FOR_FREEZE",
            reason="; ".join(failures) + ".",
            calibration_integrity_valid=True,
            validation_integrity_valid=True,
            calibration_passed=cal_passed,
            validation_passed=val_passed,
            definition_matches=definition_matches,
            freeze_at_ms_is_null=freeze_is_null,
            eligible_for_manual_freeze=False,
        )

    return FreezeReview(
        experiment_id=experiment.id,
        decision="READY_FOR_FREEZE",
        reason=(
            "Calibration and validation passed with matching definitions. "
            "A separate explicit human-controlled FROZEN transition is required."
        ),
        calibration_integrity_valid=True,
        validation_integrity_valid=True,
        calibration_passed=True,
        validation_passed=True,
        definition_matches=True,
        freeze_at_ms_is_null=True,
        eligible_for_manual_freeze=True,
    )
