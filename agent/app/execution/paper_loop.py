from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Protocol

from app.config import Settings
from app.execution.orchestrator import PaperExecutionIntent, PaperExecutionOrchestrator
from app.execution.paper import PaperBroker, PaperOrder, PaperOrderStatus
from app.market.types import MarketCandidate
from app.portfolio.models import CapitalState, LiquidityState, PortfolioPosition, PortfolioSnapshot
from app.risk.portfolio import PortfolioRiskDecision, evaluate_portfolio_risk
from app.strategies.aggregator import AggregatedAssessment, StrategyAggregator
from app.strategies.engine import StrategyEngine


class CandidateSource(Protocol):
    def run_scan(self) -> list[MarketCandidate]: ...


class PortfolioSource(Protocol):
    def get_snapshot(self) -> PortfolioSnapshot: ...


@dataclass
class StaticPortfolioSource:
    snapshot: PortfolioSnapshot

    def get_snapshot(self) -> PortfolioSnapshot:
        return self.snapshot


@dataclass(frozen=True)
class PaperCycleItem:
    symbol: str
    aggregate: AggregatedAssessment
    risk: PortfolioRiskDecision
    order: PaperOrder | None


@dataclass(frozen=True)
class PaperCycleResult:
    cycle_id: str
    enabled: bool
    items: tuple[PaperCycleItem, ...]

    @property
    def filled_orders(self) -> tuple[PaperOrder, ...]:
        return tuple(
            item.order
            for item in self.items
            if item.order is not None and item.order.status is PaperOrderStatus.FILLED
        )


def _base_asset(symbol: str) -> str:
    upper = symbol.upper()
    for quote in ("USDT", "USDC", "USD"):
        if upper.endswith(quote) and len(upper) > len(quote):
            return upper[: -len(quote)]
    return upper


def _candidate_price(candidate: MarketCandidate) -> float:
    for interval in ("1h", "4h", "15m", "1d"):
        analysis = candidate.analysis_for(interval)
        if analysis and analysis.last_price > 0:
            return analysis.last_price
    raise ValueError(f"candidate {candidate.symbol} has no usable price")


class PaperTradingLoop:
    """Disabled-by-default end-to-end paper-only loop."""

    def __init__(
        self,
        *,
        candidate_source: CandidateSource,
        portfolio_source: PortfolioSource,
        broker: PaperBroker,
        orchestrator: PaperExecutionOrchestrator,
        settings: Settings,
        strategy_engine: StrategyEngine | None = None,
        aggregator: StrategyAggregator | None = None,
    ):
        self.candidate_source = candidate_source
        self.portfolio_source = portfolio_source
        self.broker = broker
        self.orchestrator = orchestrator
        self.settings = settings
        self.strategy_engine = strategy_engine or StrategyEngine()
        self.aggregator = aggregator or StrategyAggregator()

    def _paper_overlay(
        self,
        base: PortfolioSnapshot,
        prices: dict[str, float],
        now: datetime,
    ) -> PortfolioSnapshot:
        by_asset = {position.asset.upper(): position for position in base.positions}
        cash_asset = base.cash_asset.upper()

        cash_position = by_asset.get(cash_asset)
        if cash_position is None:
            by_asset[cash_asset] = PortfolioPosition(
                asset=cash_asset,
                quantity=self.broker.account.cash_usd,
                market_value_usd=self.broker.account.cash_usd,
                capital_state=CapitalState.CASH_RESERVE,
                custody_sources=("PAPER",),
                liquidity_state=LiquidityState.LIQUID,
                liquidity_basis="paper_account",
            )
        else:
            by_asset[cash_asset] = replace(
                cash_position,
                quantity=self.broker.account.cash_usd,
                market_value_usd=self.broker.account.cash_usd,
            )

        for symbol, paper_position in self.broker.account.positions.items():
            if paper_position.quantity <= 0:
                continue
            price = prices.get(symbol.upper())
            if price is None or price <= 0:
                continue
            asset = _base_asset(symbol)
            paper_value = paper_position.quantity * price
            current = by_asset.get(asset)
            if current is None:
                by_asset[asset] = PortfolioPosition(
                    asset=asset,
                    quantity=paper_position.quantity,
                    market_value_usd=paper_value,
                    capital_state=CapitalState.CAPITAL_AT_RISK,
                    custody_sources=("PAPER",),
                    position_type="Paper",
                    liquidity_state=LiquidityState.LIQUID,
                    liquidity_basis="paper_account",
                )
            else:
                by_asset[asset] = replace(
                    current,
                    quantity=current.quantity + paper_position.quantity,
                    market_value_usd=current.market_value_usd + paper_value,
                )

        return PortfolioSnapshot(
            positions=tuple(by_asset.values()),
            allocations=base.allocations,
            cash_asset=base.cash_asset,
            daily_buy_used_usd=self.broker.daily_buy_used_usd(now),
            daily_realized_pnl_usd=self.broker.daily_realized_pnl(now),
        )

    def run_cycle(
        self,
        *,
        cycle_id: str,
        now: datetime | None = None,
    ) -> PaperCycleResult:
        if not cycle_id.strip():
            raise ValueError("cycle_id is required")
        if not self.settings.paper_loop_enabled:
            return PaperCycleResult(cycle_id=cycle_id, enabled=False, items=())

        timestamp = now or datetime.now(timezone.utc)
        candidates = self.candidate_source.run_scan()
        prices = {candidate.symbol.upper(): _candidate_price(candidate) for candidate in candidates}
        base = self.portfolio_source.get_snapshot()
        items: list[PaperCycleItem] = []

        for candidate in candidates:
            assessments = self.strategy_engine.evaluate(candidate)
            aggregate = self.aggregator.aggregate(assessments)
            current_portfolio = self._paper_overlay(base, prices, timestamp)
            risk = evaluate_portfolio_risk(aggregate, current_portfolio, self.settings)
            order = None

            if risk.approved:
                requested = min(
                    self.settings.paper_default_order_usd,
                    risk.max_notional_usd,
                )
                if requested > 0:
                    order = self.orchestrator.execute(
                        intent=PaperExecutionIntent(
                            idempotency_key=f"paper-cycle:{cycle_id}:{candidate.symbol.upper()}",
                            symbol=candidate.symbol,
                            requested_notional_usd=requested,
                        ),
                        risk=risk,
                        market_price=prices[candidate.symbol.upper()],
                        now=timestamp,
                    )
            items.append(
                PaperCycleItem(
                    symbol=candidate.symbol,
                    aggregate=aggregate,
                    risk=risk,
                    order=order,
                )
            )

        return PaperCycleResult(cycle_id=cycle_id, enabled=True, items=tuple(items))
