from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Protocol

from app.config import Settings
from app.decision.engine import DecisionEngine, DecisionEngineConfig
from app.decision.models import DecisionAction, DecisionRecord
from app.execution.orchestrator import (
    ExecutionIntentSide,
    PaperExecutionIntent,
    PaperExecutionOrchestrator,
)
from app.execution.paper import PaperBroker, PaperOrder, PaperOrderStatus
from app.market.types import MarketCandidate
from app.portfolio.models import CapitalState, LiquidityState, PortfolioPosition, PortfolioSnapshot
from app.risk.portfolio import PortfolioRiskDecision, evaluate_portfolio_risk
from app.strategies.aggregator import AggregatedAssessment, StrategyAggregator
from app.strategies.engine import StrategyEngine
from app.strategies.base import HypothesisDirection


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
    decision: DecisionRecord | None = None  # New: full decision record from DecisionEngine


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
    """Disabled-by-default end-to-end paper-only loop with DecisionEngine integration."""

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
        # New: DecisionEngine for enhanced decisions
        decision_engine: DecisionEngine | None = None,
    ):
        self.candidate_source = candidate_source
        self.portfolio_source = portfolio_source
        self.broker = broker
        self.orchestrator = orchestrator
        self.settings = settings
        self.strategy_engine = strategy_engine or StrategyEngine()
        self.aggregator = aggregator or StrategyAggregator()

        # Initialize DecisionEngine if not provided but broker/orchestrator available
        self.decision_engine = decision_engine
        if self.decision_engine is None and broker and orchestrator:
            self.decision_engine = DecisionEngine(
                settings=settings,
                config=DecisionEngineConfig(
                    default_order_usd=settings.paper_default_order_usd,
                    min_order_usd=10.0,
                    enable_journal=bool(settings.supabase_url and settings.supabase_service_role_key),
                ),
                strategy_engine=self.strategy_engine,
                aggregator=self.aggregator,
                broker=broker,
                orchestrator=orchestrator,
            )

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

        # Use DecisionEngine if available for enhanced decisions
        if self.decision_engine:
            _, decisions = self.decision_engine.run_cycle(candidates, base, cycle_id=cycle_id)

            for record in decisions:
                # Get current portfolio with paper overlay
                current_portfolio = self._paper_overlay(base, prices, timestamp)
                risk = evaluate_portfolio_risk(
                    AggregatedAssessment(
                        symbol=record.symbol,
                        state=record.aggregate_state,
                        direction=record.direction,
                        score=record.heuristic_score,
                        confidence=50.0,  # default confidence
                        supporting_strategies=(),
                        conflicting_strategies=(),
                        rejected_strategies=(),
                        reasons=(),
                    ),
                    current_portfolio,
                    self.settings,
                )

                # If DecisionEngine has an entry plan that exceeds risk capacity, override risk to BLOCKED
                # But preserve existing reasons (e.g., daily loss limit reached) which take precedence
                if record.entry_plan and record.entry_plan.position_size_usd > risk.max_notional_usd:
                    from app.risk.portfolio import PortfolioRiskDecision, RiskState
                    existing_reasons = list(risk.reasons)
                    # Only add allocation reason if not already blocked by higher-priority reason
                    if "daily loss limit reached" not in existing_reasons:
                        existing_reasons.append("asset is already at or above its maximum portfolio weight")
                    risk = PortfolioRiskDecision(
                        symbol=record.symbol,
                        state=RiskState.BLOCKED,
                        approved=False,
                        max_notional_usd=0.0,
                        reasons=tuple(existing_reasons),
                        current_asset_weight_pct=risk.current_asset_weight_pct,
                        max_asset_weight_pct=risk.max_asset_weight_pct,
                        cash_before_usd=risk.cash_before_usd,
                        cash_after_min_usd=risk.cash_after_min_usd,
                        daily_buy_remaining_usd=risk.daily_buy_remaining_usd,
                    )

                order = None
                # Execute through DecisionEngine's execute_decision
                if record.eligibility.value == "PAPER_PROPOSAL" and record.action != DecisionAction.NO_ACTION:
                    market_price = prices.get(record.symbol)
                    if market_price:
                        order = self.decision_engine.execute_decision(record, current_portfolio, market_price, cycle_id)

                items.append(
                    PaperCycleItem(
                        symbol=record.symbol,
                        aggregate=AggregatedAssessment(
                            symbol=record.symbol,
                            state=record.aggregate_state,
                            direction=record.direction,
                            score=record.heuristic_score,
                            confidence=50.0,
                            supporting_strategies=(),
                            conflicting_strategies=(),
                            rejected_strategies=(),
                            reasons=(),
                        ),
                        risk=risk,
                        order=order,
                        decision=record,
                    )
                )
        else:
            # Legacy path (backward compatibility)
            for candidate in candidates:
                assessments = self.strategy_engine.evaluate(candidate)
                aggregate = self.aggregator.aggregate(assessments)
                current_portfolio = self._paper_overlay(base, prices, timestamp)
                risk = evaluate_portfolio_risk(aggregate, current_portfolio, self.settings)
                order = None

                if risk.approved:
                    # Determine execution side from assessment direction
                    if aggregate.direction is HypothesisDirection.BUY:
                        intent_side = ExecutionIntentSide.BUY
                        requested = min(
                            self.settings.paper_default_order_usd,
                            risk.max_notional_usd,
                        )
                    elif aggregate.direction is HypothesisDirection.SELL:
                        intent_side = ExecutionIntentSide.SELL
                        # For SELL, max_notional_usd is the position value
                        requested = min(
                            self.settings.paper_default_order_usd,
                            risk.max_notional_usd,
                        )
                    else:
                        requested = 0.0
                        intent_side = ExecutionIntentSide.BUY

                    if requested > 0:
                        order = self.orchestrator.execute(
                            intent=PaperExecutionIntent(
                                idempotency_key=f"paper-cycle:{cycle_id}:{candidate.symbol.upper()}",
                                symbol=candidate.symbol,
                                side=intent_side,
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
                        decision=None,
                    )
                )

        return PaperCycleResult(cycle_id=cycle_id, enabled=True, items=tuple(items))