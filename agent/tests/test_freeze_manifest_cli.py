import json

from app.evaluation.experiment_registry import (
    ExperimentRegistry,
    ExperimentStatus,
    ResearchExperiment,
    experiment_definition_snapshot,
)
from app.evaluation.freeze_manifest_cli import main as freeze_manifest_cli_main


def test_cli_generates_manifest_without_registry_write(tmp_path, capsys):
    exp = ResearchExperiment(
        id="candidate",
        symbol="BTCUSDT",
        strategy="mean_reversion",
        direction="BUY",
        feature="volume_ratio_1h",
        operator="<=",
        threshold=0.75,
        calibration_period=None,
        validation_period=None,
        freeze_at_ms=None,
        outcome_hours=24,
        fee_bps=10.0,
        slippage_bps=5.0,
        status=ExperimentStatus.VALIDATION,
        decision=None,
        artifact_path="reports/research/candidate/",
    )
    registry = tmp_path / "registry.json"
    cal = tmp_path / "cal.json"
    val = tmp_path / "val.json"
    review = tmp_path / "review.json"
    output = tmp_path / "manifest.json"
    ExperimentRegistry((exp,)).save(registry)

    def artifact(phase, decision):
        return {
            "metadata": {
                "phase": phase,
                "experiment_id": exp.id,
                "research_only": True,
                "auto_transition": False,
                "phase6_blocked": True,
            },
            "experiment_definition": experiment_definition_snapshot(exp),
            "review": {"experiment_id": exp.id, "decision": decision},
        }

    cal.write_text(
        json.dumps(artifact("5H.6", "PASS_CALIBRATION")),
        encoding="utf-8",
    )
    val.write_text(
        json.dumps(artifact("5H.7", "PASS_VALIDATION")),
        encoding="utf-8",
    )
    review.write_text(
        json.dumps(
            {
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
                    "decision": "READY_FOR_FREEZE",
                },
            }
        ),
        encoding="utf-8",
    )
    before = registry.read_text(encoding="utf-8")

    assert freeze_manifest_cli_main(
        [
            "--registry", str(registry),
            "--experiment-id", exp.id,
            "--calibration-artifact", str(cal),
            "--validation-artifact", str(val),
            "--freeze-review-artifact", str(review),
            "--output", str(output),
        ]
    ) == 0

    assert registry.read_text(encoding="utf-8") == before
    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert manifest["metadata"]["phase"] == "5H.9"
    assert manifest["metadata"]["auto_freeze"] is False
    assert manifest["freeze_at_ms"] is None
    assert "FREEZE_MANIFEST_READY" in capsys.readouterr().out
