from app.evaluation.experiment_registry import (
    ExperimentStatus,
    ResearchExperiment,
)
from app.evaluation.freeze_manifest import canonical_json_sha256, freeze_definition
from app.evaluation.research_lineage_audit import build_lineage_audit


def experiment():
    return ResearchExperiment(
        id="future",
        symbol="BTCUSDT",
        strategy="mean_reversion",
        direction="BUY",
        feature="volume_ratio_1h",
        operator="<=",
        threshold=0.75,
        calibration_period="cal",
        validation_period="val",
        freeze_at_ms=1000,
        outcome_hours=24,
        fee_bps=10.0,
        slippage_bps=5.0,
        status=ExperimentStatus.PROSPECTIVE,
        decision="NOT_READY",
        artifact_path="reports/prospective/future/",
    )


def test_lineage_detects_fingerprint_drift():
    exp = experiment()
    definition = freeze_definition(exp)
    fingerprint = canonical_json_sha256(definition)
    artifacts = {
        "manifest": {
            "metadata": {"phase": "5H.9"},
            "experiment_id": exp.id,
            "definition_fingerprint_sha256": fingerprint,
        },
        "bootstrap": {
            "metadata": {"phase": "5H.10"},
            "protocol": {
                "experiment_id": exp.id,
                "definition_fingerprint_sha256": "bad",
            },
        },
    }
    audit = build_lineage_audit(experiment=exp, artifacts=artifacts)
    assert audit["status"] == "INVALID"
    assert any(
        not check["passed"]
        for check in audit["checks"]
        if check["name"] == "bootstrap_definition_fingerprint"
    )
