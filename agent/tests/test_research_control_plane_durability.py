import json
from datetime import datetime, timezone

from app.evaluation.experiment_registry import (
    ExperimentRegistry,
    ExperimentStatus,
    ResearchExperiment,
)
from app.evaluation.research_control_plane import build_research_control_plane
from app.evaluation.research_control_plane_material_persistence import (
    persist_material_control_plane,
)


def experiment():
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


def test_human_action_ids_are_stable(tmp_path):
    phase5g = tmp_path / "phase5g"
    phase5g.mkdir()
    (phase5g / "review.json").write_text(
        '{"state":"REVIEW_REQUIRED","progress":{"percent":100}}',
        encoding="utf-8",
    )
    (phase5g / "decision.json").write_text(
        '{"decision":"PASS_RESEARCH"}',
        encoding="utf-8",
    )
    registry = ExperimentRegistry((experiment(),))
    a = build_research_control_plane(
        registry=registry,
        phase5g_root=phase5g,
        campaign_governance_path=tmp_path / "missing-a.json",
        writer_policy_path=tmp_path / "missing-b.json",
        generated_at=datetime(2026, 11, 19, 1, tzinfo=timezone.utc),
    )
    b = build_research_control_plane(
        registry=registry,
        phase5g_root=phase5g,
        campaign_governance_path=tmp_path / "missing-a.json",
        writer_policy_path=tmp_path / "missing-b.json",
        generated_at=datetime(2026, 11, 19, 2, tzinfo=timezone.utc),
    )
    assert a["human_action_inbox"][0]["id"] == b["human_action_inbox"][0]["id"]


def test_material_persistence_skips_no_change(tmp_path):
    current = tmp_path / "current.json"
    diff = tmp_path / "diff.json"
    current.write_text(
        json.dumps({
            "phase": "5V-5Z",
            "generated_at": "2026-11-19T01:00:00+00:00",
            "snapshot_sha256": "abc",
            "blockers": [],
            "human_action_inbox": [],
            "state": "BLOCKED",
            "phase6_blocked": True,
        }),
        encoding="utf-8",
    )
    diff.write_text(
        json.dumps({
            "phase": "5Y",
            "changed": False,
            "reason": "NO_MATERIAL_CHANGE",
        }),
        encoding="utf-8",
    )
    result = persist_material_control_plane(
        current=current,
        diff=diff,
        latest=tmp_path / "latest.json",
        history_dir=tmp_path / "history",
        events_dir=tmp_path / "events",
    )
    assert result["persisted"] is False
    assert not (tmp_path / "latest.json").exists()


def test_material_persistence_writes_history_and_event(tmp_path):
    current = tmp_path / "current.json"
    diff = tmp_path / "diff.json"
    payload = {
        "phase": "5V-5Z",
        "generated_at": "2026-11-19T01:00:00+00:00",
        "snapshot_sha256": "abc",
        "blockers": [{"id": "b1"}],
        "human_action_inbox": [{"id": "a1"}],
        "state": "BLOCKED",
        "phase6_blocked": True,
    }
    current.write_text(json.dumps(payload), encoding="utf-8")
    diff.write_text(
        json.dumps({
            "phase": "5Y",
            "changed": True,
            "reason": "FIRST_SNAPSHOT",
            "previous_snapshot_sha256": None,
            "current_snapshot_sha256": "abc",
        }),
        encoding="utf-8",
    )
    result = persist_material_control_plane(
        current=current,
        diff=diff,
        latest=tmp_path / "latest.json",
        history_dir=tmp_path / "history",
        events_dir=tmp_path / "events",
    )
    assert result["persisted"] is True
    assert (tmp_path / "latest.json").exists()
    assert len(list((tmp_path / "history").glob("*.json"))) == 1
    assert len(list((tmp_path / "events").glob("*.json"))) == 1
