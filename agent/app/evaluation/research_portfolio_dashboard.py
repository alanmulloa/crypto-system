from __future__ import annotations

from typing import Any, Mapping, Sequence


def build_research_portfolio_dashboard(
    *,
    campaign_statuses: Sequence[Mapping[str, Any]],
    queues: Sequence[Mapping[str, Any]],
    registry_summary: Mapping[str, Any],
) -> dict[str, Any]:
    ready = [
        item
        for queue in queues
        for item in queue.get("queue", [])
        if item.get("decision") == "READY_FOR_HUMAN_REGISTRATION"
    ]
    campaigns = [
        {
            "campaign_id": item.get("campaign_id"),
            "state": item.get("state"),
            "screening_allowed": item.get("screening_allowed"),
        }
        for item in campaign_statuses
    ]
    return {
        "phase": "5K.8",
        "campaigns": campaigns,
        "ready_for_human_registration": ready,
        "registry": registry_summary,
        "research_only": True,
        "automatic_registration": False,
        "automatic_freeze": False,
        "phase6_blocked": True,
    }
