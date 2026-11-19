from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence


CORE_SYMBOLS = (
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "SOLUSDT",
    "XRPUSDT",
)

CAMPAIGN_STATUS = (
    "PLANNED",
    "COLLECTING",
    "SCREENING_READY",
    "SCREENED",
)


@dataclass(frozen=True)
class ResearchCampaign:
    id: str
    strategy: str
    symbols: tuple[str, ...]
    start_at: str
    end_at: str
    outcome_hours: int
    min_bucket_observations: int
    max_points: int
    fee_bps: float
    slippage_bps: float
    ruleset: str
    research_only: bool = True
    auto_register: bool = False
    auto_freeze: bool = False
    phase6_blocked: bool = True

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("campaign id is required")
        if self.strategy != "mean_reversion":
            raise ValueError("Phase 5K currently supports mean_reversion only")
        if not self.symbols:
            raise ValueError("campaign symbols are required")
        if len(set(self.symbols)) != len(self.symbols):
            raise ValueError("campaign symbols must be unique")
        if self.outcome_hours <= 0:
            raise ValueError("outcome_hours must be positive")
        if self.min_bucket_observations <= 0:
            raise ValueError("min_bucket_observations must be positive")
        if self.max_points < 60:
            raise ValueError("max_points must be at least 60")
        if self.fee_bps < 0 or self.slippage_bps < 0:
            raise ValueError("fees and slippage cannot be negative")
        if self.start_ms >= self.end_ms:
            raise ValueError("campaign start_at must precede end_at")

    @staticmethod
    def _parse(value: str) -> datetime:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @property
    def start_ms(self) -> int:
        return int(self._parse(self.start_at).timestamp() * 1000)

    @property
    def end_ms(self) -> int:
        return int(self._parse(self.end_at).timestamp() * 1000)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResearchCampaign":
        return cls(
            id=str(payload["id"]),
            strategy=str(payload["strategy"]),
            symbols=tuple(str(x).upper() for x in payload["symbols"]),
            start_at=str(payload["start_at"]),
            end_at=str(payload["end_at"]),
            outcome_hours=int(payload["outcome_hours"]),
            min_bucket_observations=int(payload["min_bucket_observations"]),
            max_points=int(payload["max_points"]),
            fee_bps=float(payload["fee_bps"]),
            slippage_bps=float(payload["slippage_bps"]),
            ruleset=str(payload["ruleset"]),
            research_only=bool(payload.get("research_only", True)),
            auto_register=bool(payload.get("auto_register", False)),
            auto_freeze=bool(payload.get("auto_freeze", False)),
            phase6_blocked=bool(payload.get("phase6_blocked", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["symbols"] = list(self.symbols)
        return payload

    def fingerprint(self) -> str:
        encoded = json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def campaign_state(
    campaign: ResearchCampaign,
    *,
    as_of_ms: int,
) -> str:
    if as_of_ms < campaign.start_ms:
        return "PLANNED"
    if as_of_ms < campaign.end_ms:
        return "COLLECTING"
    return "SCREENING_READY"


def campaign_status_payload(
    campaign: ResearchCampaign,
    *,
    as_of_ms: int,
) -> dict[str, Any]:
    state = campaign_state(campaign, as_of_ms=as_of_ms)
    return {
        "phase": "5K.2",
        "campaign_id": campaign.id,
        "campaign_fingerprint_sha256": campaign.fingerprint(),
        "state": state,
        "start_at": campaign.start_at,
        "end_at": campaign.end_at,
        "symbols": list(campaign.symbols),
        "strategy": campaign.strategy,
        "screening_allowed": state == "SCREENING_READY",
        "research_only": True,
        "auto_register": False,
        "auto_freeze": False,
        "phase6_blocked": True,
    }
