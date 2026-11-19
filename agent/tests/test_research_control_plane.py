from datetime import datetime, timezone

from app.evaluation.experiment_registry import (
    ExperimentRegistry,
    ExperimentStatus,
    ResearchExperiment,
)
from app.evaluation.research_control_plane import (
    build_research_control_plane,
    diff_control_plane,
)


def xrp():
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


def test_control_plane_remains_phase6_blocked(tmp_path):
    phase5g = tmp_path / "phase5g"
    phase5g.mkdir()
    (phase5g / "review.json").write_text(
        '{"state":"WAITING_FOR_CANDIDATE_SIGNAL","progress":{"percent":0}}',
        encoding="utf-8",
    )
    (phase5g / "decision.json").write_text(
        '{"decision":"NOT_READY"}',
        encoding="utf-8",
    )
    payload = build_research_control_plane(
        registry=ExperimentRegistry((xrp(),)),
        phase5g_root=phase5g,
        campaign_governance_path=tmp_path / "missing-campaign.json",
        writer_policy_path=tmp_path / "missing-writer.json",
        generated_at=datetime(2026, 11, 19, 12, tzinfo=timezone.utc),
    )
    assert payload["phase6_eligible"] is False
    assert payload["phase6_blocked"] is True
    assert payload["automatic_phase6_activation"] is False
    assert payload["state"] == "BLOCKED"


def test_control_plane_diff_ignores_generated_at_only():
    current = {
        "phase": "5V-5Z",
        "generated_at": "b",
        "state": "HEALTHY",
        "snapshot_sha256": "2",
        "phase6_blocked": True,
    }
    previous = {
        "phase": "5V-5Z",
        "generated_at": "a",
        "state": "HEALTHY",
        "snapshot_sha256": "1",
        "phase6_blocked": True,
    }
    diff = diff_control_plane(previous, current)
    assert diff["changed"] is False
    assert diff["reason"] == "NO_MATERIAL_CHANGE"
