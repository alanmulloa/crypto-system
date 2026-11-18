from pathlib import Path

from app.evaluation.experiment_registry import (
    ExperimentRegistry,
    ExperimentStatus,
    ResearchExperiment,
)
from app.evaluation.generic_prospective_batch_cli import run_batch


def legacy():
    return ResearchExperiment(
        id="phase5g-xrp-low-volume-1h",
        symbol="XRPUSDT",
        strategy="mean_reversion",
        direction="BUY",
        feature="volume_ratio_1h",
        operator="<=",
        threshold=0.75,
        calibration_period=None,
        validation_period=None,
        freeze_at_ms=1794348615195,
        outcome_hours=24,
        fee_bps=10.0,
        slippage_bps=5.0,
        status=ExperimentStatus.PROSPECTIVE,
        decision="NOT_READY",
        artifact_path="reports/phase5g/",
    )


def test_batch_never_routes_legacy_xrp_to_generic_builder(tmp_path: Path):
    called = False

    def builder(**kwargs):
        nonlocal called
        called = True
        return {}

    result = run_batch(
        registry=ExperimentRegistry((legacy(),)),
        reports_root=tmp_path,
        report_builder=builder,
    )
    assert called is False
    assert result["results"][0]["result"] == "LEGACY_PHASE5G_UNCHANGED"
    assert result["phase6_blocked"] is True
