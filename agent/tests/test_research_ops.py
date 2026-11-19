import json
from datetime import datetime, timezone

from app.evaluation.experiment_registry import (
    ExperimentRegistry,
    ExperimentStatus,
    ResearchExperiment,
)
from app.evaluation.research_ops import build_research_ops_report


def test_ops_report_keeps_phase6_blocked(tmp_path):
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
        freeze_at_ms=1000,
        outcome_hours=24,
        fee_bps=10.0,
        slippage_bps=5.0,
        status=ExperimentStatus.PROSPECTIVE,
        decision="NOT_READY",
        artifact_path="reports/phase5g/",
    )
    root = tmp_path / "phase5g"
    root.mkdir()
    now = datetime(2026, 11, 19, 12, tzinfo=timezone.utc)
    (root / "latest.json").write_text(
        json.dumps(
            {
                "metadata": {"created_at": now.isoformat()},
                "baseline": {"observations": 2},
                "candidate_summary": {"observations": 0, "matured": 0},
            }
        ),
        encoding="utf-8",
    )
    (root / "decision.json").write_text(
        json.dumps({"decision": "NOT_READY"}),
        encoding="utf-8",
    )
    report = build_research_ops_report(
        registry=ExperimentRegistry((exp,)),
        phase5g_root=root,
        generic_root=tmp_path / "generic",
        as_of=now,
    )
    row = report["experiments"][0]
    assert row["state"] == "HEALTHY_WAITING_FOR_SIGNAL"
    assert row["recommended_action"] == "CONTINUE_COLLECTION"
    assert row["phase6_blocked"] is True
