from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class CampaignIncident:
    severity: str
    code: str
    detail: str


def detect_campaign_incidents(
    report: Mapping[str, Any],
) -> tuple[CampaignIncident, ...]:
    incidents: list[CampaignIncident] = []
    readiness = report.get("screening_readiness") or {}
    data_health = report.get("data_health") or {}

    if readiness.get("fingerprint_matches") is False:
        incidents.append(
            CampaignIncident(
                severity="CRITICAL",
                code="CAMPAIGN_DRIFT",
                detail="Pre-registered campaign fingerprint changed.",
            )
        )

    if data_health.get("all_symbols_healthy") is False:
        incidents.append(
            CampaignIncident(
                severity="HIGH",
                code="MARKET_DATA_UNHEALTHY",
                detail="At least one campaign symbol/interval is unhealthy.",
            )
        )

    for symbol in data_health.get("symbols") or []:
        if symbol.get("spot_available") is False:
            incidents.append(
                CampaignIncident(
                    severity="CRITICAL",
                    code="SPOT_UNAVAILABLE",
                    detail=f"{symbol.get('symbol')} is not Spot-available.",
                )
            )
        for interval in symbol.get("intervals") or []:
            if interval.get("gap_count", 0) > 0:
                incidents.append(
                    CampaignIncident(
                        severity="HIGH",
                        code="INTERVAL_GAP",
                        detail=(
                            f"{symbol.get('symbol')} "
                            f"{interval.get('interval')} has gaps."
                        ),
                    )
                )
            if interval.get("duplicate_open_times", 0) > 0:
                incidents.append(
                    CampaignIncident(
                        severity="HIGH",
                        code="DUPLICATE_CANDLES",
                        detail=(
                            f"{symbol.get('symbol')} "
                            f"{interval.get('interval')} has duplicates."
                        ),
                    )
                )
            if interval.get("fresh") is False:
                incidents.append(
                    CampaignIncident(
                        severity="MEDIUM",
                        code="STALE_CANDLES",
                        detail=(
                            f"{symbol.get('symbol')} "
                            f"{interval.get('interval')} is stale."
                        ),
                    )
                )

    return tuple(incidents)


def incidents_to_dict(
    incidents: tuple[CampaignIncident, ...],
) -> dict[str, Any]:
    return {
        "phase": "5M.3",
        "incident_count": len(incidents),
        "incidents": [asdict(item) for item in incidents],
        "research_only": True,
        "automatic_strategy_change": False,
        "phase6_blocked": True,
    }
