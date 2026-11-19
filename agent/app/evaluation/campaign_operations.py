from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from app.evaluation.experiment_registry import ExperimentRegistry
from app.evaluation.research_campaign import ResearchCampaign, campaign_state
from app.evaluation.research_portfolio_dashboard import (
    build_research_portfolio_dashboard,
)
from app.market.binance_public import BinancePublicClient, INTERVAL_MS
from app.market.types import Candle


DAY_MS = 24 * 60 * 60 * 1000
REQUIRED_INTERVALS = ("15m", "1h", "4h", "1d")


@dataclass(frozen=True)
class CampaignProgress:
    campaign_id: str
    state: str
    elapsed_days: float
    remaining_days: float
    duration_days: float
    progress_pct: float
    screening_allowed: bool


@dataclass(frozen=True)
class IntervalHealth:
    interval: str
    candles: int
    duplicate_open_times: int
    gap_count: int
    latest_close_time_ms: int | None
    age_ms: int | None
    fresh: bool
    healthy: bool


@dataclass(frozen=True)
class ScreeningReadiness:
    campaign_id: str
    state: str
    time_window_complete: bool
    data_health_ok: bool
    fingerprint_matches: bool
    screening_allowed: bool
    recommended_action: str
    auto_screening: bool = False
    auto_register: bool = False
    phase6_blocked: bool = True


def build_campaign_progress(
    campaign: ResearchCampaign,
    *,
    as_of_ms: int,
) -> CampaignProgress:
    duration_ms = campaign.end_ms - campaign.start_ms
    elapsed_ms = min(
        max(as_of_ms - campaign.start_ms, 0),
        duration_ms,
    )
    remaining_ms = max(campaign.end_ms - as_of_ms, 0)
    state = campaign_state(campaign, as_of_ms=as_of_ms)
    return CampaignProgress(
        campaign_id=campaign.id,
        state=state,
        elapsed_days=elapsed_ms / DAY_MS,
        remaining_days=remaining_ms / DAY_MS,
        duration_days=duration_ms / DAY_MS,
        progress_pct=elapsed_ms / duration_ms * 100.0,
        screening_allowed=state == "SCREENING_READY",
    )


def evaluate_interval_health(
    interval: str,
    candles: Sequence[Candle],
    *,
    as_of_ms: int,
) -> IntervalHealth:
    if interval not in INTERVAL_MS:
        raise ValueError(f"unsupported interval: {interval}")
    if not candles:
        return IntervalHealth(
            interval=interval,
            candles=0,
            duplicate_open_times=0,
            gap_count=0,
            latest_close_time_ms=None,
            age_ms=None,
            fresh=False,
            healthy=False,
        )

    opens = [item.open_time_ms for item in candles]
    duplicate_count = len(opens) - len(set(opens))
    step = INTERVAL_MS[interval]
    gap_count = sum(
        1
        for previous, current in zip(opens, opens[1:])
        if current - previous > step
    )
    latest_close = candles[-1].close_time_ms
    age_ms = max(0, as_of_ms - latest_close)
    fresh = age_ms <= step * 2
    return IntervalHealth(
        interval=interval,
        candles=len(candles),
        duplicate_open_times=duplicate_count,
        gap_count=gap_count,
        latest_close_time_ms=latest_close,
        age_ms=age_ms,
        fresh=fresh,
        healthy=duplicate_count == 0 and gap_count == 0 and fresh,
    )


def probe_campaign_data(
    *,
    campaign: ResearchCampaign,
    client: BinancePublicClient | None = None,
    as_of_ms: int | None = None,
) -> dict[str, Any]:
    market = client or BinancePublicClient()
    effective_as_of = as_of_ms or market.now_ms()
    exchange_info = {
        item.symbol: item
        for item in market.exchange_info()
    }
    symbols: list[dict[str, Any]] = []

    for symbol in campaign.symbols:
        info = exchange_info.get(symbol)
        intervals: list[dict[str, Any]] = []
        for interval in REQUIRED_INTERVALS:
            step = INTERVAL_MS[interval]
            candles = tuple(
                market.historical_klines(
                    symbol,
                    interval,
                    start_time_ms=max(0, effective_as_of - step * 4),
                    end_time_ms=effective_as_of,
                    page_limit=10,
                )
            )
            intervals.append(
                asdict(
                    evaluate_interval_health(
                        interval,
                        candles,
                        as_of_ms=effective_as_of,
                    )
                )
            )
        spot_available = bool(info and info.spot_allowed)
        symbols.append(
            {
                "symbol": symbol,
                "spot_available": spot_available,
                "intervals": intervals,
                "healthy": spot_available
                and all(item["healthy"] for item in intervals),
            }
        )

    return {
        "phase": "5L.2",
        "campaign_id": campaign.id,
        "campaign_fingerprint_sha256": campaign.fingerprint(),
        "as_of_ms": effective_as_of,
        "all_symbols_healthy": all(item["healthy"] for item in symbols),
        "symbols": symbols,
        "research_only": True,
        "candidate_selection_performed": False,
        "phase6_blocked": True,
    }


def build_screening_readiness(
    *,
    campaign: ResearchCampaign,
    progress: CampaignProgress,
    data_health: Mapping[str, Any],
) -> ScreeningReadiness:
    fingerprint_matches = (
        data_health.get("campaign_fingerprint_sha256")
        == campaign.fingerprint()
    )
    data_ok = data_health.get("all_symbols_healthy") is True
    window_complete = progress.screening_allowed
    screening_allowed = window_complete and data_ok and fingerprint_matches

    if not fingerprint_matches:
        state = "BLOCKED_CAMPAIGN_DRIFT"
        action = "RESTORE_PREREGISTERED_CAMPAIGN"
    elif not data_ok:
        state = "BLOCKED_DATA_HEALTH"
        action = "CHECK_PUBLIC_MARKET_DATA"
    elif not window_complete:
        state = "COLLECTING"
        action = "CONTINUE_FIXED_WINDOW"
    else:
        state = "READY_FOR_HUMAN_SCREENING"
        action = "RUN_FIXED_CAMPAIGN_SCREEN"

    return ScreeningReadiness(
        campaign_id=campaign.id,
        state=state,
        time_window_complete=window_complete,
        data_health_ok=data_ok,
        fingerprint_matches=fingerprint_matches,
        screening_allowed=screening_allowed,
        recommended_action=action,
    )


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_campaign_operations(
    *,
    campaign: ResearchCampaign,
    registry: ExperimentRegistry,
    reports_root: Path,
    as_of_ms: int,
    data_health: Mapping[str, Any],
) -> dict[str, Any]:
    progress = build_campaign_progress(campaign, as_of_ms=as_of_ms)
    readiness = build_screening_readiness(
        campaign=campaign,
        progress=progress,
        data_health=data_health,
    )
    queue = _read_json(reports_root / "promotion-queue.json")
    dashboard = build_research_portfolio_dashboard(
        campaign_statuses=(
            {
                "campaign_id": campaign.id,
                "state": progress.state,
                "screening_allowed": readiness.screening_allowed,
            },
        ),
        queues=(queue,) if queue is not None else (),
        registry_summary={
            "experiments": len(registry.experiments),
            "prospective": sum(
                item.status.value == "PROSPECTIVE"
                for item in registry.experiments
            ),
        },
    )
    generated_at = datetime.fromtimestamp(
        as_of_ms / 1000,
        tz=timezone.utc,
    ).isoformat()
    return {
        "phase": "5L.5",
        "generated_at": generated_at,
        "campaign_id": campaign.id,
        "campaign_fingerprint_sha256": campaign.fingerprint(),
        "progress": asdict(progress),
        "data_health": dict(data_health),
        "screening_readiness": asdict(readiness),
        "portfolio_dashboard": dashboard,
        "research_only": True,
        "automatic_screening": False,
        "automatic_registration": False,
        "phase6_blocked": True,
    }


def build_live_campaign_operations(
    *,
    campaign: ResearchCampaign,
    registry: ExperimentRegistry,
    reports_root: Path,
) -> dict[str, Any]:
    data_health = probe_campaign_data(campaign=campaign)
    return build_campaign_operations(
        campaign=campaign,
        registry=registry,
        reports_root=reports_root,
        as_of_ms=int(data_health["as_of_ms"]),
        data_health=data_health,
    )
