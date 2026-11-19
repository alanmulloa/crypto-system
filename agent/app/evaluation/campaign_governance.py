from __future__ import annotations

from typing import Any, Mapping


def build_campaign_governance_status(
    *,
    review_pack: Mapping[str, Any],
    reproducibility: Mapping[str, Any],
) -> dict[str, Any]:
    review_state = str(review_pack.get("state") or "")
    reproducible = bool(
        reproducibility.get("source_artifacts_immutable") is True
        and reproducibility.get("automatic_repair") is False
    )

    healthy = review_state in {"COLLECTING", "READY_FOR_HUMAN_SCREENING"}
    return {
        "phase": "5Q",
        "campaign_id": review_pack.get("campaign_id"),
        "operationally_healthy": healthy,
        "reproducibility_valid": reproducible,
        "review_state": review_state,
        "next_action": review_pack.get("next_action"),
        "research_only": True,
        "automatic_strategy_change": False,
        "automatic_screening": False,
        "automatic_registration": False,
        "automatic_freeze": False,
        "phase6_eligible": False,
        "phase6_blocked": True,
        "operations_hardening_complete": healthy and reproducible,
    }
