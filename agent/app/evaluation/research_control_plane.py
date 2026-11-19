from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from app.evaluation.experiment_registry import ExperimentRegistry


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_dependency_status(
    *,
    phase5g_review: Mapping[str, Any] | None,
    phase5g_decision: Mapping[str, Any] | None,
    phase5m_latest: Mapping[str, Any] | None,
    phase5m_incidents: Mapping[str, Any] | None,
    campaign_governance: Mapping[str, Any] | None,
    writer_policy: Mapping[str, Any] | None,
) -> dict[str, Any]:
    phase5g_ready = phase5g_review is not None and phase5g_decision is not None
    campaign_inputs_ready = (
        phase5m_latest is not None and phase5m_incidents is not None
    )
    campaign_governance_ready = (
        campaign_governance is not None if campaign_inputs_ready else False
    )
    writer_policy_ready = (
        writer_policy is not None and writer_policy.get("all_compliant") is True
    )

    missing: list[str] = []
    if not phase5g_ready:
        missing.append("PHASE5G_EVIDENCE")
    if not campaign_inputs_ready:
        missing.append("PHASE5M_DURABLE_INPUTS")
    elif not campaign_governance_ready:
        missing.append("PHASE5NQ_GOVERNANCE")
    if not writer_policy_ready:
        missing.append("WRITER_POLICY")

    return {
        "phase": "5AH",
        "phase5g_ready": phase5g_ready,
        "campaign_inputs_ready": campaign_inputs_ready,
        "campaign_governance_ready": campaign_governance_ready,
        "writer_policy_ready": writer_policy_ready,
        "ready": not missing,
        "missing": missing,
        "research_only": True,
        "phase6_blocked": True,
    }


def build_research_control_plane(
    *,
    registry: ExperimentRegistry,
    phase5g_root: Path,
    campaign_governance_path: Path,
    writer_policy_path: Path,
    phase5m_root: Path | None = None,
    generated_at: datetime,
) -> dict[str, Any]:
    phase5g_review = _read_json(phase5g_root / "review.json")
    phase5g_decision = _read_json(phase5g_root / "decision.json")
    campaign_governance = _read_json(campaign_governance_path)
    writer_policy = _read_json(writer_policy_path)
    phase5m_latest = (
        _read_json(phase5m_root / "latest.json")
        if phase5m_root is not None
        else None
    )
    phase5m_incidents = (
        _read_json(phase5m_root / "incidents.json")
        if phase5m_root is not None
        else None
    )
    dependencies = build_dependency_status(
        phase5g_review=phase5g_review,
        phase5g_decision=phase5g_decision,
        phase5m_latest=phase5m_latest,
        phase5m_incidents=phase5m_incidents,
        campaign_governance=campaign_governance,
        writer_policy=writer_policy,
    )

    experiments = []
    human_actions = []
    blockers = []

    def stable_id(kind: str, subject: str | None) -> str:
        return _sha({"kind": kind, "subject": subject})[:16]

    for item in registry.experiments:
        row = {
            "experiment_id": item.id,
            "symbol": item.symbol,
            "strategy": item.strategy,
            "status": item.status.value,
            "phase6_blocked": True,
        }
        if item.id == "phase5g-xrp-low-volume-1h":
            state = (
                phase5g_review.get("state")
                if phase5g_review is not None
                else "MISSING_REVIEW"
            )
            decision = (
                phase5g_decision.get("decision")
                if phase5g_decision is not None
                else item.decision
            )
            row.update(
                {
                    "pipeline": "PHASE5G_LEGACY",
                    "state": state,
                    "research_decision": decision,
                    "progress": (
                        phase5g_review.get("progress")
                        if phase5g_review is not None
                        else None
                    ),
                }
            )
            if decision == "PASS_RESEARCH":
                human_actions.append(
                    {
                        "id": stable_id("HUMAN_PHASE6_REVIEW_REQUIRED", item.id),
                        "type": "HUMAN_PHASE6_REVIEW_REQUIRED",
                        "subject": item.id,
                    }
                )
            elif decision == "FAIL_RESEARCH":
                human_actions.append(
                    {
                        "id": stable_id("HUMAN_RESEARCH_REVIEW_REQUIRED", item.id),
                        "type": "HUMAN_RESEARCH_REVIEW_REQUIRED",
                        "subject": item.id,
                    }
                )
            else:
                blockers.append(
                    {
                        "id": stable_id("PROSPECTIVE_SAMPLE_INCOMPLETE", item.id),
                        "code": "PROSPECTIVE_SAMPLE_INCOMPLETE",
                        "subject": item.id,
                    }
                )
        else:
            row.update(
                {
                    "pipeline": "GENERIC_5H",
                    "state": item.status.value,
                    "research_decision": item.decision,
                }
            )
        experiments.append(row)

    if campaign_governance is None:
        campaign = {
            "state": "WAITING_FOR_FIRST_DURABLE_GOVERNANCE_ARTIFACT",
            "phase6_blocked": True,
        }
        blockers.append(
            {
                "id": stable_id(
                    "CAMPAIGN_GOVERNANCE_NOT_YET_AVAILABLE",
                    "core-mean-reversion-forward-2026-11",
                ),
                "code": "CAMPAIGN_GOVERNANCE_NOT_YET_AVAILABLE",
                "subject": "core-mean-reversion-forward-2026-11",
            }
        )
    else:
        campaign = dict(campaign_governance)
        if campaign.get("review_state") in {
            "ATTENTION_INCIDENTS",
            "BLOCKED_CRITICAL_INCIDENT",
        }:
            human_actions.append(
                {
                    "type": "HUMAN_CAMPAIGN_INCIDENT_REVIEW",
                    "subject": campaign.get("campaign_id"),
                }
            )
        if campaign.get("review_state") == "READY_FOR_HUMAN_SCREENING":
            human_actions.append(
                {
                    "type": "RUN_FIXED_CAMPAIGN_SCREEN",
                    "subject": campaign.get("campaign_id"),
                }
            )

    writer = (
        dict(writer_policy)
        if writer_policy is not None
        else {
            "state": "WAITING_FOR_POLICY_ARTIFACT",
            "phase6_blocked": True,
        }
    )
    if writer_policy is not None and writer_policy.get("all_compliant") is not True:
        blockers.append(
            {
                "id": stable_id(
                    "RESEARCH_MAIN_WRITER_POLICY_NONCOMPLIANT",
                    "research-main-writer",
                ),
                "code": "RESEARCH_MAIN_WRITER_POLICY_NONCOMPLIANT",
                "subject": "research-main-writer",
            }
        )

    state = (
        "HUMAN_ACTION_REQUIRED"
        if human_actions
        else "WAITING_FOR_DEPENDENCIES"
        if dependencies.get("ready") is not True
        else "BLOCKED"
        if blockers
        else "HEALTHY"
    )
    core = {
        "phase": "5V-5Z",
        "generated_at": generated_at.astimezone(timezone.utc).isoformat(),
        "state": state,
        "experiments": experiments,
        "campaign": campaign,
        "writer_policy": writer,
        "dependencies": dependencies,
        "blockers": blockers,
        "human_action_inbox": human_actions,
        "research_only": True,
        "automatic_strategy_change": False,
        "automatic_registration": False,
        "automatic_screening": False,
        "automatic_freeze": False,
        "automatic_phase6_activation": False,
        "phase6_eligible": False,
        "phase6_blocked": True,
    }
    core["snapshot_sha256"] = _sha(core)
    return core


def diff_control_plane(
    previous: Mapping[str, Any] | None,
    current: Mapping[str, Any],
) -> dict[str, Any]:
    if previous is None:
        return {
            "phase": "5Y",
            "changed": True,
            "reason": "FIRST_SNAPSHOT",
            "previous_snapshot_sha256": None,
            "current_snapshot_sha256": current.get("snapshot_sha256"),
            "phase6_blocked": True,
        }

    previous_core = {
        key: value
        for key, value in previous.items()
        if key not in {"generated_at", "snapshot_sha256"}
    }
    current_core = {
        key: value
        for key, value in current.items()
        if key not in {"generated_at", "snapshot_sha256"}
    }
    changed = previous_core != current_core
    return {
        "phase": "5Y",
        "changed": changed,
        "reason": "STATE_CHANGED" if changed else "NO_MATERIAL_CHANGE",
        "previous_snapshot_sha256": previous.get("snapshot_sha256"),
        "current_snapshot_sha256": current.get("snapshot_sha256"),
        "phase6_blocked": True,
    }
