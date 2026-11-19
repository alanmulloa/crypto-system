import json
from datetime import datetime, timezone

from app.evaluation.experiment_registry import ExperimentRegistry
from app.evaluation.research_control_plane import (
    build_dependency_status,
    build_research_control_plane,
)


def write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_dependency_status_reports_campaign_bootstrap_gap():
    payload = build_dependency_status(
        phase5g_review={"state": "WAITING"},
        phase5g_decision={"decision": "NOT_READY"},
        phase5m_latest=None,
        phase5m_incidents=None,
        campaign_governance=None,
        writer_policy={"all_compliant": True},
    )
    assert payload["ready"] is False
    assert payload["phase5g_ready"] is True
    assert payload["writer_policy_ready"] is True
    assert payload["missing"] == ["PHASE5M_DURABLE_INPUTS"]


def test_control_plane_uses_waiting_for_dependencies(tmp_path):
    phase5g = tmp_path / "phase5g"
    phase5g.mkdir()
    write(phase5g / "review.json", {"state": "WAITING"})
    write(phase5g / "decision.json", {"decision": "NOT_READY"})
    write(tmp_path / "policy.json", {"all_compliant": True})

    payload = build_research_control_plane(
        registry=ExperimentRegistry(()),
        phase5g_root=phase5g,
        campaign_governance_path=tmp_path / "governance.json",
        writer_policy_path=tmp_path / "policy.json",
        phase5m_root=tmp_path / "phase5m",
        generated_at=datetime(2026, 11, 19, 12, tzinfo=timezone.utc),
    )
    assert payload["state"] == "WAITING_FOR_DEPENDENCIES"
    assert payload["dependencies"]["missing"] == ["PHASE5M_DURABLE_INPUTS"]
    assert payload["phase6_blocked"] is True
