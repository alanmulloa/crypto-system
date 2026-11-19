from pathlib import Path

from app.evaluation.experiment_registry import (
    ExperimentRegistry,
    ExperimentStatus,
    ResearchExperiment,
)
from app.evaluation.research_dossier import build_research_dossier


def test_dossier_never_marks_phase6_eligible(tmp_path: Path):
    exp = ResearchExperiment(
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
    dossier = build_research_dossier(
        registry=ExperimentRegistry((exp,)),
        reports_root=tmp_path / "prospective",
        phase5g_root=tmp_path / "phase5g",
    )
    row = dossier["experiments"][0]
    assert row["phase6_eligible"] is False
    assert row["phase6_blocked"] is True
    assert row["next_allowed_action"] == "CONTINUE_PROSPECTIVE_COLLECTION"
