import json

import pytest

from app.evaluation.experiment_registry import (
    ExperimentRegistry,
    ExperimentStatus,
    ResearchExperiment,
    experiment_definition_snapshot,
)
from app.evaluation.freeze_manifest import (
    build_freeze_manifest,
    canonical_json_sha256,
)


def experiment(**changes):
    values = {
        "id": "btc-low-volume",
        "symbol": "BTCUSDT",
        "strategy": "mean_reversion",
        "direction": "BUY",
        "feature": "volume_ratio_1h",
        "operator": "<=",
        "threshold": 0.75,
        "calibration_period": "cal",
        "validation_period": "val",
        "freeze_at_ms": None,
        "outcome_hours": 24,
        "fee_bps": 10.0,
        "slippage_bps": 5.0,
        "status": ExperimentStatus.VALIDATION,
        "decision": None,
        "artifact_path": "reports/research/btc-low-volume/",
    }
    values.update(changes)
    return ResearchExperiment(**values)


def stage_artifact(exp, phase, decision):
    return {
        "metadata": {
            "phase": phase,
            "experiment_id": exp.id,
            "research_only": True,
            "auto_transition": False,
            "phase6_blocked": True,
        },
        "experiment_definition": experiment_definition_snapshot(exp),
        "review": {
            "experiment_id": exp.id,
            "decision": decision,
        },
    }


def freeze_review_artifact(exp, decision="READY_FOR_FREEZE"):
    return {
        "metadata": {
            "phase": "5H.8",
            "experiment_id": exp.id,
            "research_only": True,
            "auto_transition": False,
            "auto_freeze": False,
            "phase6_blocked": True,
        },
        "review": {
            "experiment_id": exp.id,
            "decision": decision,
        },
    }


def build(exp):
    calibration = stage_artifact(exp, "5H.6", "PASS_CALIBRATION")
    validation = stage_artifact(exp, "5H.7", "PASS_VALIDATION")
    freeze_review = freeze_review_artifact(exp)
    return build_freeze_manifest(
        experiment=exp,
        calibration_artifact=calibration,
        validation_artifact=validation,
        freeze_review_artifact=freeze_review,
        calibration_path="cal.json",
        validation_path="val.json",
        freeze_review_path="freeze.json",
        created_at="2026-11-13T00:00:00+00:00",
    )


def test_manifest_contains_deterministic_definition_fingerprint():
    exp = experiment()
    first = build(exp)
    second = build(exp)
    assert first["definition_fingerprint_sha256"] == second[
        "definition_fingerprint_sha256"
    ]
    assert first["definition_fingerprint_sha256"] == canonical_json_sha256(
        first["frozen_definition"]
    )
    assert first["freeze_at_ms"] is None
    assert first["freeze_timestamp_pending"] is True


def test_manifest_records_artifact_hashes_and_decisions():
    manifest = build(experiment())
    assert manifest["calibration"]["decision"] == "PASS_CALIBRATION"
    assert manifest["validation"]["decision"] == "PASS_VALIDATION"
    assert len(manifest["calibration"]["sha256"]) == 64
    assert len(manifest["validation"]["sha256"]) == 64
    assert manifest["metadata"]["auto_freeze"] is False
    assert manifest["metadata"]["phase6_blocked"] is True


def test_manifest_rejects_non_ready_freeze_review():
    exp = experiment()
    with pytest.raises(ValueError, match="READY_FOR_FREEZE"):
        build_freeze_manifest(
            experiment=exp,
            calibration_artifact=stage_artifact(
                exp, "5H.6", "PASS_CALIBRATION"
            ),
            validation_artifact=stage_artifact(
                exp, "5H.7", "PASS_VALIDATION"
            ),
            freeze_review_artifact=freeze_review_artifact(
                exp, "NOT_READY_FOR_FREEZE"
            ),
            calibration_path="cal.json",
            validation_path="val.json",
            freeze_review_path="freeze.json",
            created_at="now",
        )


def test_manifest_rechecks_artifacts_instead_of_trusting_gate():
    exp = experiment()
    validation = stage_artifact(exp, "5H.7", "PASS_VALIDATION")
    validation["experiment_definition"]["threshold"] = 0.70
    with pytest.raises(ValueError, match="no longer satisfy"):
        build_freeze_manifest(
            experiment=exp,
            calibration_artifact=stage_artifact(
                exp, "5H.6", "PASS_CALIBRATION"
            ),
            validation_artifact=validation,
            freeze_review_artifact=freeze_review_artifact(exp),
            calibration_path="cal.json",
            validation_path="val.json",
            freeze_review_path="freeze.json",
            created_at="now",
        )


def test_manifest_requires_validation_status_and_null_freeze():
    with pytest.raises(ValueError, match="status VALIDATION"):
        build(experiment(status=ExperimentStatus.CALIBRATION))

    frozen = experiment(status=ExperimentStatus.FROZEN, freeze_at_ms=123)
    with pytest.raises(ValueError):
        build(frozen)


def test_registry_serialization_unchanged_by_manifest(tmp_path):
    exp = experiment()
    path = tmp_path / "registry.json"
    ExperimentRegistry((exp,)).save(path)
    before = path.read_text(encoding="utf-8")
    build(exp)
    assert path.read_text(encoding="utf-8") == before
