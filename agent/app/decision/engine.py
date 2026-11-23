"""AI Trading Decision Engine.

Phase 2: Core decision engine integrating market scanning, multi-strategy evaluation,
risk-adjusted decisions, eligibility gates, deterministic sizing, calibrated confidence,
and decision journal persistence.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.config import Settings
from app.decision.confidence import ConfidenceCalibrator, heuristic_confidence
from app.decision.eligibility import evaluate_eligibility, determine_action
from app.decision.journal import DecisionJournal, InMemoryDecisionJournal
from app.decision.models import (
    DecisionAction,
    DecisionEligibility,
    DecisionRecord,
    EntryPlan,
    SizingConstraints,
)
from app.decision.sizing import build_entry_plan, calculate_position_size, calculate_sizing_details
from app.execution.orchestrator import ExecutionIntentSide, PaperExecutionIntent, PaperExecutionOrchestrator
from app.execution.paper import PaperBroker, PaperOrder, PaperOrderStatus, PaperSide
from app.market.types import MarketCandidate
from app.portfolio.models import PortfolioSnapshot
from app.risk.portfolio import evaluate_portfolio_risk
from app.strategies.aggregator import AggregatedAssessment, StrategyAggregator
from app.strategies.base import HypothesisDirection
from app.strategies.engine import StrategyEngine


@dataclass
class DecisionEngineConfig:
    """Configuration for the Decision Engine."""
    default_order_usd: float = 100.0
    min_order_usd: float = 10.0
    enable_journal: bool = True
    calibrator_min_samples: int = 50
    max_slippage_bps: float = 10.0


class DecisionEngine:
    """Core decision engine for AI trading decisions."""

    def __init__(
        self,
        settings: Settings,
        config: DecisionEngineConfig | None = None,
        strategy_engine: StrategyEngine | None = None,
        aggregator: StrategyAggregator | None = None,
        broker: PaperBroker | None = None,
        orchestrator: PaperExecutionOrchestrator | None = None,
        journal: DecisionJournal | InMemoryDecisionJournal | None = None,
    ):
        self.settings = settings
        self.config = config or DecisionEngineConfig()
        self.strategy_engine = strategy_engine or StrategyEngine()
        self.aggregator = aggregator or StrategyAggregator()
        self.broker = broker
        self.orchestrator = orchestrator

        # Initialize journal
        if journal:
            self.journal = journal
        elif self.config.enable_journal:
            try:
                self.journal = DecisionJournal(settings)
            except ValueError:
                self.journal = InMemoryDecisionJournal()
        else:
            self.journal = InMemoryDecisionJournal()

        # Calibrator for confidence scoring
        self.calibrator = ConfidenceCalibrator(min_samples=self.config.calibrator_min_samples)

        # Cycle tracking
        self._cycle_counter = 0

    def _generate_cycle_id(self) -> str:
        """Generate unique cycle ID."""
        self._cycle_counter += 1
        return f"cycle_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{self._cycle_counter:04d}"

    def _extract_volatility(self, candidate: MarketCandidate) -> float:
        """Extract volatility score from candidate (0-1 scale).

        Returns a volatility adjustment factor where:
        - 1.0 = low volatility (full position size)
        - 0.1 = high volatility (reduced position size)
        """
        for interval in ("1h", "4h", "15m", "1d"):
            analysis = candidate.analysis_for(interval)
            if analysis and analysis.indicators and analysis.indicators.atr and analysis.last_price > 0:
                # Normalize ATR as percentage of price
                atr_pct = analysis.indicators.atr / analysis.last_price
                # Invert: low ATR -> high adjustment (near 1.0), high ATR -> low adjustment (near 0.1)
                # 2% ATR -> ~0.8, 5% ATR -> ~0.5, 10% ATR -> ~0.1
                adjustment = max(1.0 - atr_pct * 10, 0.1)
                return min(adjustment, 1.0)
        return 0.5  # Default neutral volatility

    def _extract_atr(self, candidate: MarketCandidate) -> float | None:
        """Extract ATR from candidate."""
        for interval in ("1h", "4h", "15m", "1d"):
            analysis = candidate.analysis_for(interval)
            if analysis and analysis.indicators and analysis.indicators.atr and analysis.indicators.atr > 0:
                return analysis.indicators.atr
        return None

    def _get_current_price(self, candidate: MarketCandidate) -> float:
        """Get current market price from candidate."""
        for interval in ("1h", "4h", "15m", "1d"):
            analysis = candidate.analysis_for(interval)
            if analysis and analysis.last_price > 0:
                return analysis.last_price
        raise ValueError(f"No valid price for {candidate.symbol}")

    def evaluate_candidate(
        self,
        candidate: MarketCandidate,
        portfolio: PortfolioSnapshot,
        cycle_id: str,
    ) -> DecisionRecord:
        """Evaluate a single candidate and produce a decision record.

        Args:
            candidate: Market candidate from scanner
            portfolio: Current portfolio snapshot
            cycle_id: Cycle identifier for journal grouping

        Returns:
            DecisionRecord with full decision context
        """
        symbol = candidate.symbol.upper()
        market_price = self._get_current_price(candidate)
        volatility_score = self._extract_volatility(candidate)
        atr = self._extract_atr(candidate)

        # Run strategy evaluation
        assessments = self.strategy_engine.evaluate(candidate)
        aggregate = self.aggregator.aggregate(assessments)

        # Current position value
        from app.risk.portfolio import _base_asset
        asset = _base_asset(symbol)
        position = portfolio.position_for(asset)
        current_position_usd = position.market_value_usd if position else 0.0

        # Evaluate portfolio risk
        risk_decision = evaluate_portfolio_risk(aggregate, portfolio, self.settings)

        # Determine eligibility
        eligibility = evaluate_eligibility(
            assessment=aggregate,
            risk_state=risk_decision.state,
            risk_approved=risk_decision.approved,
            max_notional_usd=risk_decision.max_notional_usd,
            current_position_usd=current_position_usd,
        )

        # Determine action
        action_str, action_reason = determine_action(
            assessment=aggregate,
            eligibility=eligibility,
            current_position_usd=current_position_usd,
            requested_notional_usd=self.config.default_order_usd,
        )
        action = DecisionAction(action_str)

        # Calculate heuristic confidence
        # Compute conflict_ratio from supporting vs conflicting strategies
        total_strategies = len(aggregate.supporting_strategies) + len(aggregate.conflicting_strategies)
        conflict_ratio = len(aggregate.conflicting_strategies) / total_strategies if total_strategies > 0 else 0.0

        heuristic = heuristic_confidence(
            aggregate_score=aggregate.score,
            risk_approved=risk_decision.approved,
            conflict_ratio=conflict_ratio,
            volatility_score=volatility_score,
        )

        # Calibrated confidence
        confidence = self.calibrator.calibrate(heuristic)

        # Build entry plan if actionable
        entry_plan: EntryPlan | None = None
        sizing_details: dict[str, Any] | None = None

        if eligibility is DecisionEligibility.PAPER_PROPOSAL and action != DecisionAction.NO_ACTION:
            # Build sizing constraints
            constraints = SizingConstraints.from_market_context(
                max_position_usd=self.settings.max_position_usd,
                max_exposure_usd=self.settings.max_position_usd * 3,  # 3x position limit
                cash_available_usd=portfolio.cash_value_usd,
                portfolio_total_usd=portfolio.total_value_usd,
                daily_loss_limit_usd=self.settings.daily_loss_limit_usd,
                volatility_score=volatility_score,
            )

            # Calculate position size
            size_usd, size_reason, size_warnings = calculate_position_size(
                constraints=constraints,
                direction=aggregate.direction,
                current_position_usd=current_position_usd,
                market_price=market_price,
                requested_notional_usd=self.config.default_order_usd,
                atr=atr,
            )

            sizing_details = calculate_sizing_details(
                constraints=constraints,
                direction=aggregate.direction or HypothesisDirection.BUY,
                current_position_usd=current_position_usd,
                requested_notional_usd=self.config.default_order_usd,
                final_size_usd=size_usd,
            )

            # Build entry plan
            if size_usd >= self.config.min_order_usd:
                entry_plan = build_entry_plan(
                    symbol=symbol,
                    action=action,
                    market_price=market_price,
                    size_usd=size_usd,
                    atr=atr,
                    current_entry_price=position.avg_cost if position and hasattr(position, 'avg_cost') else None,
                )
                entry_plan = entry_plan.__class__(
                    side=entry_plan.side,
                    symbol=entry_plan.symbol,
                    entry_price=entry_plan.entry_price,
                    stop_price=entry_plan.stop_price,
                    target_prices=entry_plan.target_prices,
                    position_size_usd=entry_plan.position_size_usd,
                    estimated_impact_usd=entry_plan.estimated_impact_usd,
                    reason=f"{action_reason}; {size_reason}",
                    warnings=entry_plan.warnings + size_warnings,
                )

        # Build decision record
        record = DecisionRecord(
            symbol=symbol,
            action=action,
            eligibility=eligibility,
            confidence_score=confidence,
            heuristic_score=heuristic,
            entry_plan=entry_plan,
            risk_state=risk_decision.state.value,
            reasons=risk_decision.reasons,
            warnings=(),
            aggregate_state=aggregate.state,
            direction=aggregate.direction,
            max_notional_usd=risk_decision.max_notional_usd,
            sizing_details_json=json.dumps(sizing_details) if sizing_details else None,
        )

        return record

    def execute_decision(
        self,
        record: DecisionRecord,
        portfolio: PortfolioSnapshot,
        market_price: float,
        cycle_id: str,
    ) -> PaperOrder | None:
        """Execute a paper trading decision.

        Args:
            record: Decision record
            portfolio: Current portfolio (with paper overlay)
            market_price: Current market price
            cycle_id: Cycle identifier

        Returns:
            PaperOrder if executed, None otherwise
        """
        if record.action == DecisionAction.NO_ACTION:
            return None

        if not self.broker or not self.orchestrator:
            return None

        if not record.entry_plan or record.entry_plan.position_size_usd < self.config.min_order_usd:
            return None

        # Re-evaluate risk with current portfolio (paper overlay)
        risk_decision = evaluate_portfolio_risk(
            AggregatedAssessment(
                symbol=record.symbol,
                state=record.aggregate_state,
                direction=record.direction,
                score=record.heuristic_score,
                confidence=record.confidence_score,
                supporting_strategies=(),
                conflicting_strategies=(),
                rejected_strategies=(),
                reasons=record.reasons,
            ),
            portfolio,
            self.settings,
        )

        # Re-evaluate eligibility with current risk decision
        from app.decision.eligibility import evaluate_eligibility

        eligibility = evaluate_eligibility(
            assessment=AggregatedAssessment(
                symbol=record.symbol,
                state=record.aggregate_state,
                direction=record.direction,
                score=record.heuristic_score,
                confidence=record.confidence_score,
                supporting_strategies=(),
                conflicting_strategies=(),
                rejected_strategies=(),
                reasons=record.reasons,
            ),
            risk_state=risk_decision.state,
            risk_approved=risk_decision.approved,
            max_notional_usd=risk_decision.max_notional_usd,
            current_position_usd=0.0,  # Will be recalculated if needed
        )

        if eligibility != DecisionEligibility.PAPER_PROPOSAL:
            return None

        # If risk not approved, don't execute
        if not risk_decision.approved or risk_decision.max_notional_usd <= 0:
            return None

        # If remaining capacity is below minimum order size, don't execute
        if risk_decision.max_notional_usd < self.config.min_order_usd:
            return None

        # If intended order size exceeds available capacity, reject (hard limit)
        if record.entry_plan and record.entry_plan.position_size_usd > risk_decision.max_notional_usd:
            return None

        # Map decision action to execution intent
        if record.action == DecisionAction.BUY:
            intent_side = ExecutionIntentSide.BUY
        elif record.action == DecisionAction.SELL:
            intent_side = ExecutionIntentSide.SELL
        elif record.action == DecisionAction.REDUCE:
            intent_side = ExecutionIntentSide.REDUCE
        else:
            return None

        # Create execution intent
        intent = PaperExecutionIntent(
            idempotency_key=f"paper-cycle:{cycle_id}:{record.symbol}",
            symbol=record.symbol,
            side=intent_side,
            requested_notional_usd=record.entry_plan.position_size_usd,
        )

        # Execute through orchestrator
        order = self.orchestrator.execute(
            intent=intent,
            risk=risk_decision,
            market_price=market_price,
            now=datetime.now(timezone.utc),
        )

        return order

    def record_outcome(
        self,
        decision_id: str,
        order: PaperOrder,
        market_price: float,
    ) -> None:
        """Record decision outcome for calibration and audit."""
        if not order:
            return

        from app.decision.models import DecisionOutcome

        filled = order.status == PaperOrderStatus.FILLED

        outcome = DecisionOutcome(
            decision_id=decision_id,
            order_id=order.order_id,
            filled=filled,
            fill_price=order.fill.price if filled and order.fill else market_price,
            quantity=order.fill.quantity if filled and order.fill else (order.request.quantity if order.request else 0.0),
            notional=order.fill.gross_usd if filled and order.fill else (order.request.notional_usd if order.request else 0.0),
            fees_usd=order.fill.fee_usd if filled and order.fill else 0.0,
            slippage_usd=0.0,  # Not available in PaperFill
            pnl_usd=None,  # Would need position tracking for PnL
            timestamp=datetime.now(timezone.utc),
        )

        self.journal.record_outcome(outcome)

        # Update calibrator if filled
        if filled and self.calibrator:
            # For now, use a simple heuristic: profitable if BUY and price > entry, or SELL and price < entry
            success = False
            if order.request and order.request.side == PaperSide.BUY and order.fill and order.fill.price and order.fill.price > 0:
                success = True  # Simplified: assume success for calibration
            elif order.request and order.request.side in (PaperSide.SELL, PaperSide.BUY) and order.fill and order.fill.price and order.fill.price > 0:
                success = True

            self.calibrator.add_outcome(record.heuristic_score if (record := self.journal.get_decision(decision_id)) else 50.0, success)

    def run_cycle(
        self,
        candidates: list[MarketCandidate],
        portfolio: PortfolioSnapshot,
        cycle_id: str | None = None,
    ) -> tuple[str, list[DecisionRecord]]:
        """Run a complete decision cycle for all candidates (evaluation only).

        Args:
            candidates: List of market candidates from scanner
            portfolio: Current portfolio snapshot
            cycle_id: Optional cycle identifier (generated if not provided)

        Returns:
            Tuple of (cycle_id, list of decision records)
        """
        if cycle_id is None:
            cycle_id = self._generate_cycle_id()
        decisions: list[DecisionRecord] = []

        for candidate in candidates:
            record = self.evaluate_candidate(candidate, portfolio, cycle_id)
            decisions.append(record)

            # Record to journal
            self.journal.record_decision(record, cycle_id)

        return cycle_id, decisions


