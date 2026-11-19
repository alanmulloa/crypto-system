from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.config import Settings


@dataclass(frozen=True)
class RiskPreflight:
    trading_mode: str
    binance_testnet: bool
    kill_switch: bool
    max_position_usd: float
    max_daily_buy_usd: float
    min_cash_reserve_pct: float
    max_open_positions: int
    daily_loss_limit_usd: float
    private_api_key_configured: bool
    private_api_secret_configured: bool
    safe_for_readiness_review: bool
    phase6_blocked: bool
    detail: str


def build_risk_preflight(settings: Settings) -> RiskPreflight:
    safe = (
        settings.trading_mode == "PAPER"
        and settings.binance_testnet is True
        and settings.kill_switch is True
        and settings.max_position_usd > 0
        and settings.max_daily_buy_usd > 0
        and settings.min_cash_reserve_pct >= 0
        and settings.max_open_positions > 0
        and settings.daily_loss_limit_usd > 0
    )
    return RiskPreflight(
        trading_mode=settings.trading_mode,
        binance_testnet=settings.binance_testnet,
        kill_switch=settings.kill_switch,
        max_position_usd=settings.max_position_usd,
        max_daily_buy_usd=settings.max_daily_buy_usd,
        min_cash_reserve_pct=settings.min_cash_reserve_pct,
        max_open_positions=settings.max_open_positions,
        daily_loss_limit_usd=settings.daily_loss_limit_usd,
        private_api_key_configured=bool(settings.binance_api_key),
        private_api_secret_configured=bool(settings.binance_api_secret),
        safe_for_readiness_review=safe,
        phase6_blocked=True,
        detail=(
            "Paper mode, Testnet target and active kill switch are configured."
            if safe
            else "Runtime safety settings are not ready for Phase 6 review."
        ),
    )


def risk_preflight_to_dict(value: RiskPreflight) -> dict[str, Any]:
    return asdict(value)
