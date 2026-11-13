import json

from app.evaluation.experiment_registry import (
    ExperimentStatus,
    ResearchExperiment,
    experiment_definition_snapshot,
)
from app.evaluation.freeze_review import review_freeze_readiness
from app.evaluation.freeze_review_cli import main as freeze_review_cli_main


def experiment(**changes):
    values = {
        "id": "btc-low-volume",
        "symbol": "BTCUSDT",
        "strategy": "mean_reversion",
        "direction": "BUY",
        "feature": "volume_ratio_1h",
        "operator": "<=",
        "threshold": 0.75,
        "calibration_period": None,
        "validation_period": None,
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


def artifact(exp, phase, decision):
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


def test_ready_when_both_pass_and_definition_matches():
    exp = experiment()
    result = review_freeze_readiness(
        experiment=exp,
        calibration_artifact=artifact(exp, "5H.6", "PASS_CALIBRATION"),
        validation_artifact=artifact(exp, "5H.7", "PASS_VALIDATION"),
    )
    assert result.decision == "READY_FOR_FREEZE"
    assert result.eligible_for_manual_freeze is True
    assert result.auto_transition is False
    assert result.auto_freeze is False
    assert result.phase6_blocked is True


def test_failed_validation_is_not_ready():
    exp = experiment()
    result = review_freeze_readiness(
        experiment=exp,
        calibration_artifact=artifact(exp, "5H.6", "PASS_CALIBRATION"),
        validation_artifact=artifact(exp, "5H.7", "FAIL_VALIDATION"),
    )
    assert result.decision == "NOT_READY_FOR_FREEZE"


def test_definition_drift_is_not_ready():
    exp = experiment()
    validation = artifact(exp, "5H.7", "PASS_VALIDATION")
    validation["experiment_definition"]["threshold"] = 0.70
    result = review_freeze_readiness(
        experiment=exp,
        calibration_artifact=artifact(exp, "5H.6", "PASS_CALIBRATION"),
        validation_artifact=validation,
    )
    assert result.decision == "NOT_READY_FOR_FREEZE"
    assert result.definition_matches is False


def test_missing_definition_snapshot_is_inconclusive():
    exp = experiment()
    calibration = artifact(exp, "5H.6", "PASS_CALIBRATION")
    calibration.pop("experiment_definition")
    result = review_freeze_readiness(
        experiment=exp,
        calibration_artifact=calibration,
        validation_artifact=artifact(exp, "5H.7", "PASS_VALIDATION"),
    )
    assert result.decision == "INCONCLUSIVE"


def test_wrong_registry_status_is_not_ready():
    exp = experiment(status=ExperimentStatus.CALIBRATION)
    result = review_freeze_readiness(
        experiment=exp,
        calibration_artifact=artifact(exp, "5H.6", "PASS_CALIBRATION"),
        validation_artifact=artifact(exp, "5H.7", "PASS_VALIDATION"),
    )
    assert result.decision == "NOT_READY_FOR_FREEZE"


def test_existing_freeze_timestamp_is_not_ready():
    exp = experiment(status=ExperimentStatus.FROZEN, freeze_at_ms=123)
    result = review_freeze_readiness(
        experiment=exp,
        calibration_artifact=artifact(exp, "5H.6", "PASS_CALIBRATION"),
        validation_artifact=artifact(exp, "5H.7", "PASS_VALIDATION"),
    )
    assert result.decision == "NOT_READY_FOR_FREEZE"


def test_cli_writes_gate_without_registry_side_effect(tmp_path, capsys):
    from app.evaluation.experiment_registry import ExperimentRegistry

    exp = experiment()
    registry = tmp_path / "registry.json"
    calibration = tmp_path / "calibration.json"
    validation = tmp_path / "validation.json"
    output = tmp_path / "freeze-review.json"

    ExperimentRegistry((exp,)).save(registry)
    calibration.write_text(
        json.dumps(artifact(exp, "5H.6", "PASS_CALIBRATION")),
        encoding="utf-8",
    )
    validation.write_text(
        json.dumps(artifact(exp, "5H.7", "PASS_VALIDATION")),
        encoding="utf-8",
    )
    before = registry.read_text(encoding="utf-8")

    assert freeze_review_cli_main(
        [
            "--registry", str(registry),
            "--experiment-id", exp.id,
            "--calibration-artifact", str(calibration),
            "--validation-artifact", str(validation),
            "--output", str(output),
        ]
    ) == 0

    assert registry.read_text(encoding="utf-8") == before
    assert "READY_FOR_FREEZE" in capsys.readouterr().out
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["metadata"]["auto_freeze"] is False
    assert payload["metadata"]["phase6_blocked"] is True
