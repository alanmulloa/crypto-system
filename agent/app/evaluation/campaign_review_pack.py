from __future__ import annotations

from typing import Any, Mapping


def build_campaign_review_pack(
    *,
    operations: Mapping[str, Any],
    incidents: Mapping[str, Any],
    recovery: Mapping[str, Any],
    reproducibility: Mapping[str, Any],
) -> dict[str, Any]:
    readiness = operations.get("screening_readiness") or {}
    progress = operations.get("progress") or {}
    incident_count = int(incidents.get("incident_count", 0))
    highest = str(recovery.get("highest_severity") or "NONE")

    if highest == "CRITICAL":
        state = "BLOCKED_CRITICAL_INCIDENT"
        next_action = "HUMAN_INCIDENT_REVIEW"
    elif incident_count > 0:
        state = "ATTENTION_INCIDENTS"
        next_action = "REVIEW_RECOVERY_PLAN"
    elif readiness.get("screening_allowed") is True:
        state = "READY_FOR_HUMAN_SCREENING"
        next_action = "RUN_FIXED_CAMPAIGN_SCREEN"
    else:
        state = "COLLECTING"
        next_action = "CONTINUE_FIXED_WINDOW"

    return {
        "phase": "5P",
        "campaign_id": operations.get("campaign_id"),
        "state": state,
        "next_action": next_action,
        "progress_pct": progress.get("progress_pct"),
        "remaining_days": progress.get("remaining_days"),
        "screening_readiness": readiness,
        "incident_count": incident_count,
        "highest_incident_severity": highest,
        "recovery_actions": recovery.get("actions") or [],
        "reproducibility_manifest": reproducibility,
        "research_only": True,
        "human_review_required": state != "COLLECTING",
        "automatic_screening": False,
        "automatic_registration": False,
        "phase6_blocked": True,
    }
