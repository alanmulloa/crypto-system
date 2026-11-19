from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from app.evaluation.research_campaign import ResearchCampaign


FIRST_DAY_MS = 24 * 60 * 60 * 1000


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_campaign_launch_status(
    *,
    campaign: ResearchCampaign,
    launch_seal: Mapping[str, Any],
    operations: Mapping[str, Any],
    as_of_ms: int,
) -> dict[str, Any]:
    sealed_definition = launch_seal.get("sealed_definition")
    if not isinstance(sealed_definition, dict):
        raise ValueError("launch seal missing sealed_definition")

    sealed_campaign = ResearchCampaign.from_dict(sealed_definition)
    definition_matches = (
        campaign.to_dict() == sealed_campaign.to_dict()
        and campaign.fingerprint() == sealed_campaign.fingerprint()
    )
    health_ok = (
        (operations.get("data_health") or {}).get("all_symbols_healthy")
        is True
    )
    screening_allowed = (
        (operations.get("screening_readiness") or {}).get(
            "screening_allowed"
        )
        is True
    )

    if not definition_matches:
        state = "BLOCKED_DEFINITION_DRIFT"
        action = "RESTORE_SEALED_CAMPAIGN"
    elif as_of_ms < campaign.start_ms:
        state = "PRESTART_READY" if health_ok else "PRESTART_DATA_ATTENTION"
        action = (
            "WAIT_FOR_CAMPAIGN_START"
            if health_ok
            else "CHECK_PUBLIC_MARKET_DATA"
        )
    elif as_of_ms < campaign.start_ms + FIRST_DAY_MS:
        state = "FIRST_DAY_HEALTHY" if health_ok else "FIRST_DAY_ATTENTION"
        action = (
            "CONTINUE_FIXED_WINDOW"
            if health_ok
            else "CHECK_PUBLIC_MARKET_DATA"
        )
    elif as_of_ms < campaign.end_ms:
        state = "COLLECTING" if health_ok else "COLLECTING_DATA_ATTENTION"
        action = (
            "CONTINUE_FIXED_WINDOW"
            if health_ok
            else "CHECK_PUBLIC_MARKET_DATA"
        )
    else:
        state = (
            "READY_FOR_HUMAN_SCREENING"
            if screening_allowed
            else "POST_WINDOW_REVIEW_REQUIRED"
        )
        action = (
            "RUN_FIXED_CAMPAIGN_SCREEN"
            if screening_allowed
            else "REVIEW_CAMPAIGN_HEALTH"
        )

    return {
        "phase": "5AK-5AO",
        "campaign_id": campaign.id,
        "state": state,
        "recommended_action": action,
        "campaign_fingerprint_sha256": campaign.fingerprint(),
        "sealed_fingerprint_sha256": sealed_campaign.fingerprint(),
        "definition_matches_seal": definition_matches,
        "start_at": campaign.start_at,
        "end_at": campaign.end_at,
        "as_of_ms": as_of_ms,
        "first_day_window": (
            campaign.start_ms <= as_of_ms
            < campaign.start_ms + FIRST_DAY_MS
        ),
        "data_health_ok": health_ok,
        "screening_allowed": screening_allowed,
        "screening_before_end_forbidden": True,
        "threshold_optimization_forbidden": True,
        "research_only": True,
        "automatic_screening": False,
        "automatic_registration": False,
        "automatic_freeze": False,
        "phase6_eligible": False,
        "phase6_blocked": True,
    }


def build_campaign_launch_status_from_files(
    *,
    campaign_path: Path,
    seal_path: Path,
    operations_path: Path,
) -> dict[str, Any]:
    campaign = ResearchCampaign.from_dict(_load(campaign_path))
    seal = _load(seal_path)
    operations = _load(operations_path)
    as_of_ms = int(
        operations.get("data_health", {}).get("as_of_ms")
        or operations.get("progress", {}).get("as_of_ms")
        or datetime.now(timezone.utc).timestamp() * 1000
    )
    return build_campaign_launch_status(
        campaign=campaign,
        launch_seal=seal,
        operations=operations,
        as_of_ms=as_of_ms,
    )
