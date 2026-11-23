from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.config import Settings
from app.portfolio.models import PortfolioSnapshot
from app.strategies.aggregator import AggregatedAssessment
from app.strategies.base import HypothesisDirection, StrategyState


class RiskState(str, Enum):
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"
    NO_ACTION = "NO_ACTION"


@dataclass(frozen=True)
class PortfolioRiskDecision:
    symbol: str
    state: RiskState
    approved: bool
    max_notional_usd: float
    reasons: tuple[str, ...] = field(default_factory=tuple)
    current_asset_weight_pct: float = 0.0
    max_asset_weight_pct: float | None = None
    cash_before_usd: float = 0.0
    cash_after_min_usd: float = 0.0
    daily_buy_remaining_usd: float = 0.0


def _base_asset(
    symbol: str, quote_assets: tuple[str, ...] = ("USDT", "USDC", "USD")
) -> str:
    upper = symbol.upper()
    for quote in quote_assets:
        if upper.endswith(quote) and len(upper) > len(quote):
            return upper[: -len(quote)]
    return upper


def evaluate_portfolio_risk(
    assessment: AggregatedAssessment,
    portfolio: PortfolioSnapshot,
    settings: Settings,
    custody_sources: tuple[str, ...] | None = None,
) -> PortfolioRiskDecision:
    asset = _base_asset(assessment.symbol)
    reasons: list[str] = []

    # Helper to get values with optional custody filtering
    def get_weight() -> float:
        return portfolio.weight_pct(asset, custody_sources=custody_sources)

    def get_position() -> PortfolioSnapshot | None:
        return portfolio.position_for(asset, custody_sources=custody_sources)

    def get_cash() -> float:
        return portfolio.cash_value_usd(custody_sources=custody_sources)

    def get_total() -> float:
        return portfolio.total_value_usd(custody_sources=custody_sources)

    def get_open_positions() -> int:
        if custody_sources is None:
            return portfolio.open_positions()
        cash = portfolio.cash_asset.upper()
        return sum(
            1
            for position in portfolio.positions
            if position.asset.upper() != cash
            and position.market_value_usd > 0
            and any(s in position.custody_sources for s in custody_sources)
        )

    if assessment.state is StrategyState.REJECT or assessment.direction is None:
        return PortfolioRiskDecision(
            symbol=assessment.symbol,
            state=RiskState.NO_ACTION,
            approved=False,
            max_notional_usd=0.0,
            reasons=("research assessment has no actionable direction",),
            current_asset_weight_pct=get_weight(),
            cash_before_usd=get_cash(),
            daily_buy_remaining_usd=max(
                settings.max_daily_buy_usd - portfolio.daily_buy_used_usd, 0.0
            ),
        )

    if assessment.direction is HypothesisDirection.SELL:
        position = get_position()
        if position is None or position.market_value_usd <= 0:
            return PortfolioRiskDecision(
                symbol=assessment.symbol,
                state=RiskState.NO_ACTION,
                approved=False,
                max_notional_usd=0.0,
                reasons=("spot-only system cannot short an asset that is not held",),
                current_asset_weight_pct=0.0,
                cash_before_usd=get_cash(),
                daily_buy_remaining_usd=max(
                    settings.max_daily_buy_usd - portfolio.daily_buy_used_usd, 0.0
                ),
            )
        # Allow SELL/REDUCE for paper trading when we have a position to reduce
        # The max notional is the current position value (can sell up to full position)
        max_sell_notional = position.market_value_usd

        # Apply risk checks for SELL (kill switch, position limits, etc.)
        if settings.kill_switch:
            reasons.append("kill switch is active")

        # For SELL, we don't need cash reserve or daily buy limit checks
        # but we should still respect max position constraints
        allocation = portfolio.allocation_for(asset)
        current_weight = get_weight()
        max_weight = allocation.max_weight_pct if allocation else None

        approved = not reasons and assessment.state is StrategyState.WATCH
        if not approved:
            max_sell_notional = 0.0

        return PortfolioRiskDecision(
            symbol=assessment.symbol,
            state=RiskState.APPROVED if approved else RiskState.BLOCKED,
            approved=approved,
            max_notional_usd=max_sell_notional,
            reasons=tuple(dict.fromkeys(reasons)),
            current_asset_weight_pct=current_weight,
            max_asset_weight_pct=max_weight,
            cash_before_usd=get_cash(),
            cash_after_min_usd=get_cash() + max_sell_notional,
            daily_buy_remaining_usd=max(
                settings.max_daily_buy_usd - portfolio.daily_buy_used_usd, 0.0
            ),
        )

    if assessment.state is not StrategyState.WATCH:
        reasons.append("aggregate state is not WATCH")

    if settings.kill_switch:
        reasons.append("kill switch is active")

    if get_open_positions() >= settings.max_open_positions and get_position() is None:
        reasons.append("maximum number of open positions reached")

    if not portfolio.daily_loss_guard_available:
        reasons.append(
            "daily realized PnL is unavailable; daily loss guard cannot be verified"
        )
    elif (
        portfolio.daily_realized_pnl_usd is not None
        and portfolio.daily_realized_pnl_usd <= -abs(settings.daily_loss_limit_usd)
    ):
        reasons.append("daily loss limit reached")

    cash = get_cash()
    total = get_total()
    reserve_pct = settings.min_cash_reserve_pct / 100.0
    required_reserve = total * reserve_pct
    reserve_headroom = max(cash - required_reserve, 0.0)

    daily_remaining = max(
        settings.max_daily_buy_usd - portfolio.daily_buy_used_usd, 0.0
    )
    if daily_remaining <= 0:
        reasons.append("daily buy limit reached")

    allocation = portfolio.allocation_for(asset)
    current_weight = get_weight()
    max_weight = allocation.max_weight_pct if allocation else None
    allocation_headroom = float("inf")
    if max_weight is not None:
        max_asset_value = total * (max_weight / 100.0)
        current_position = get_position()
        current_asset_value = (
            current_position.market_value_usd if current_position else 0.0
        )
        allocation_headroom = max(max_asset_value - current_asset_value, 0.0)
        if allocation_headroom <= 0:
            reasons.append("asset is already at or above its maximum portfolio weight")

    hard_notional = max(settings.max_position_usd, 0.0)
    max_notional = min(
        hard_notional, reserve_headroom, daily_remaining, allocation_headroom
    )

    if cash <= 0:
        reasons.append("no cash reserve available")
    if reserve_headroom <= 0:
        reasons.append("minimum cash reserve prevents new allocation")
    if max_notional <= 0:
        reasons.append("no notional capacity remains after hard risk constraints")

    approved = not reasons and assessment.state is StrategyState.WATCH
    if not approved:
        max_notional = 0.0

    return PortfolioRiskDecision(
        symbol=assessment.symbol,
        state=RiskState.APPROVED if approved else RiskState.BLOCKED,
        approved=approved,
        max_notional_usd=max_notional,
        reasons=tuple(dict.fromkeys(reasons)),
        current_asset_weight_pct=current_weight,
        max_asset_weight_pct=max_weight,
        cash_before_usd=cash,
        cash_after_min_usd=required_reserve,
        daily_buy_remaining_usd=daily_remaining,
    )
