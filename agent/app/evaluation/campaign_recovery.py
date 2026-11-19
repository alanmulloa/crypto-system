from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class RecoveryAction:
    incident_code: str
    severity: str
    action: str
    automatic: bool
    strategy_change_allowed: bool
    registry_write_allowed: bool
    phase6_blocked: bool = True


_ACTIONS = {
    "CAMPAIGN_DRIFT": "RESTORE_PREREGISTERED_CAMPAIGN_DEFINITION",
    "MARKET_DATA_UNHEALTHY": "CHECK_PUBLIC_MARKET_DATA_PIPELINE",
    "SPOT_UNAVAILABLE": "PAUSE_AFFECTED_SYMBOL_RESEARCH_REVIEW",
    "INTERVAL_GAP": "RECOLLECT_AND_COMPARE_PUBLIC_CANDLES",
    "DUPLICATE_CANDLES": "REBUILD_DEDUPLICATED_MARKET_WINDOW",
    "STALE_CANDLES": "CHECK_COLLECTION_FRESHNESS",
}


def build_recovery_plan(
    incidents_payload: Mapping[str, Any],
) -> dict[str, Any]:
    actions: list[RecoveryAction] = []
    for item in incidents_payload.get("incidents") or []:
        code = str(item.get("code"))
        severity = str(item.get("severity"))
        action = _ACTIONS.get(code, "HUMAN_REVIEW_REQUIRED")
        actions.append(
            RecoveryAction(
                incident_code=code,
                severity=severity,
                action=action,
                automatic=False,
                strategy_change_allowed=False,
                registry_write_allowed=False,
            )
        )

    highest = "NONE"
    order = {"NONE": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    for item in actions:
        if order.get(item.severity, 0) > order.get(highest, 0):
            highest = item.severity

    return {
        "phase": "5N",
        "incident_count": len(actions),
        "highest_severity": highest,
        "actions": [asdict(item) for item in actions],
        "research_only": True,
        "automatic_recovery": False,
        "automatic_strategy_change": False,
        "automatic_registry_write": False,
        "phase6_blocked": True,
    }
