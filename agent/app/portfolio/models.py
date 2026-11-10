from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CapitalState(str, Enum):
    PROFITS_ONLY = "PROFITS_ONLY"
    CAPITAL_AT_RISK = "CAPITAL_AT_RISK"
    RECOVERED_REVIEW = "RECOVERED_REVIEW"
    PARTIAL_RECONSTRUCTION = "PARTIAL_RECONSTRUCTION"
    CASH_RESERVE = "CASH_RESERVE"
    UNKNOWN = "UNKNOWN"


class LiquidityState(str, Enum):
    LIQUID = "LIQUID"
    STAKED = "STAKED"
    POOLED = "POOLED"
    LOCKED = "LOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class PortfolioPosition:
    asset: str
    quantity: float
    market_value_usd: float
    avg_cost_usd: float | None = None
    capital_pending_usd: float | None = None
    capital_state: CapitalState = CapitalState.UNKNOWN
    custody_sources: tuple[str, ...] = field(default_factory=tuple)
    position_type: str | None = None
    liquidity_state: LiquidityState = LiquidityState.UNKNOWN
    liquidity_basis: str | None = None

    def __post_init__(self) -> None:
        if self.quantity < 0:
            raise ValueError("quantity cannot be negative")
        if self.market_value_usd < 0:
            raise ValueError("market_value_usd cannot be negative")
        if self.capital_pending_usd is not None and self.capital_pending_usd < 0:
            raise ValueError("capital_pending_usd cannot be negative")


@dataclass(frozen=True)
class AllocationTarget:
    asset: str
    target_weight_pct: float | None = None
    max_weight_pct: float | None = None
    priority: str | None = None

    def __post_init__(self) -> None:
        for value in (self.target_weight_pct, self.max_weight_pct):
            if value is not None and not 0 <= value <= 100:
                raise ValueError("allocation percentages must be between 0 and 100")
        if (
            self.target_weight_pct is not None
            and self.max_weight_pct is not None
            and self.target_weight_pct > self.max_weight_pct
        ):
            raise ValueError("target_weight_pct cannot exceed max_weight_pct")


@dataclass(frozen=True)
class PortfolioSnapshot:
    positions: tuple[PortfolioPosition, ...]
    allocations: tuple[AllocationTarget, ...] = field(default_factory=tuple)
    cash_asset: str = "USDC"
    daily_buy_used_usd: float = 0.0
    daily_realized_pnl_usd: float | None = None

    def __post_init__(self) -> None:
        if self.daily_buy_used_usd < 0:
            raise ValueError("daily_buy_used_usd cannot be negative")

    @property
    def total_value_usd(self) -> float:
        return sum(position.market_value_usd for position in self.positions)

    @property
    def cash_value_usd(self) -> float:
        cash = self.cash_asset.upper()
        return sum(
            position.market_value_usd
            for position in self.positions
            if position.asset.upper() == cash
        )

    @property
    def open_positions(self) -> int:
        cash = self.cash_asset.upper()
        return sum(
            position.market_value_usd > 0
            for position in self.positions
            if position.asset.upper() != cash
        )

    @property
    def daily_loss_guard_available(self) -> bool:
        return self.daily_realized_pnl_usd is not None

    def position_for(self, asset: str) -> PortfolioPosition | None:
        needle = asset.upper()
        return next(
            (position for position in self.positions if position.asset.upper() == needle),
            None,
        )

    def allocation_for(self, asset: str) -> AllocationTarget | None:
        needle = asset.upper()
        return next(
            (allocation for allocation in self.allocations if allocation.asset.upper() == needle),
            None,
        )

    def weight_pct(self, asset: str) -> float:
        total = self.total_value_usd
        if total <= 0:
            return 0.0
        position = self.position_for(asset)
        return (position.market_value_usd / total * 100.0) if position else 0.0

    @property
    def capital_at_risk_usd(self) -> float:
        total = 0.0
        for position in self.positions:
            if position.capital_state is CapitalState.PROFITS_ONLY:
                continue
            if position.capital_state is CapitalState.CASH_RESERVE:
                continue
            if position.capital_pending_usd is not None:
                total += min(position.capital_pending_usd, position.market_value_usd)
            elif position.capital_state in {
                CapitalState.CAPITAL_AT_RISK,
                CapitalState.PARTIAL_RECONSTRUCTION,
                CapitalState.RECOVERED_REVIEW,
                CapitalState.UNKNOWN,
            }:
                total += position.market_value_usd
        return total
