"""Decision models for the AI Trading Decision Engine.

Phase 2: Core decision models with eligibility gates, deterministic sizing, and journal entry.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from app.strategies.base import HypothesisDirection, StrategyState


class DecisionAction(str, Enum):
    """Core decision action types."""
    BUY = "BUY"
    SELL = "SELL"
    REDUCE = "REDUCE"  # Partial sell (position reduction)
    NO_ACTION = "NO_ACTION"


class DecisionEligibility(str, Enum):
    """Eligibility gate states for trading decisions.

    - RESEARCH_ONLY: Strategy signaled but aggregate state is WATCH/PASS_RESEARCH,
      NOT eligible for actual paper trading execution.
    - BLOCKED: Risk constraints prevent trading.
    - PAPER_PROPOSAL: Eligible for paper trading (default for approved BUY/SELL/REDUCE).
    """
    RESEARCH_ONLY = "RESEARCH_ONLY"
    BLOCKED = "BLOCKED"
    PAPER_PROPOSAL = "PAPER_PROPOSAL"


@dataclass(frozen=True)
class SizingConstraints:
    """Deterministic sizing constraints for position sizing calculations."""
    max_position_usd: float  # Absolute position size limit
    max_exposure_usd: float  # Portfolio exposure limit
    min_liquidity_usd: float  # Minimum cash/liquidity requirement
    max_cash_drawdown_usd: float  # Maximum allowable cash reduction
    max_daily_loss_usd: float  # Daily loss guard limit
    volatility_adjustment: float  # Volatility-based sizing factor (0.0-1.0)

    @classmethod
    def from_market_context(
        cls,
        max_position_usd: float,
        max_exposure_usd: float,
        cash_available_usd: float,
        portfolio_total_usd: float,
        daily_loss_limit_usd: float,
        volatility_score: float = 0.5,  # 0-1 scale, 0.5 = neutral
    ) -> SizingConstraints:
        """Create sizing constraints from market and portfolio context."""
        reserve_pct = 0.10  # Default 10% cash reserve
        min_cash = portfolio_total_usd * reserve_pct

        return cls(
            max_position_usd=max_position_usd,
            max_exposure_usd=max_exposure_usd,
            min_liquidity_usd=min_cash,
            max_cash_drawdown_usd=min(cash_available_usd - min_cash, cash_available_usd),
            max_daily_loss_usd=daily_loss_limit_usd,
            volatility_adjustment=volatility_score,
        )


@dataclass(frozen=True)
class EntryPlan:
    """Entry/exit plan with null handling for undefined values."""
    side: DecisionAction  # BUY, SELL, or REDUCE
    symbol: str
    entry_price: float | None  # Target entry price (None if not determined)
    stop_price: float | None  # Stop loss level
    target_prices: tuple[float, ...]  # Take profit levels
    position_size_usd: float  # Target position size in USD
    estimated_impact_usd: float  # Estimated slippage/market impact
    reason: str  # Primary reason for this plan
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON storage."""
        return {
            "side": self.side.value,
            "symbol": self.symbol,
            "entry_price": self.entry_price,
            "stop_price": self.stop_price,
            "target_prices": self.target_prices,
            "position_size_usd": self.position_size_usd,
            "estimated_impact_usd": self.estimated_impact_usd,
            "reason": self.reason,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class DecisionRecord:
    """Single trading decision with full context."""
    symbol: str
    action: DecisionAction
    eligibility: DecisionEligibility
    confidence_score: float  # 0-100 calibrated confidence
    heuristic_score: float  # Raw strategy score (fallback when calibrated unavailable)
    entry_plan: EntryPlan | None
    risk_state: str  # RiskState enum value
    reasons: tuple[str, ...]  # Aggregated reasons from risk evaluation
    warnings: tuple[str, ...] = field(default_factory=tuple)
    # Extra context for journal (optional)
    aggregate_state: StrategyState | None = None
    direction: HypothesisDirection | None = None
    max_notional_usd: float = 0.0
    sizing_details_json: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize for storage."""
        return {
            "symbol": self.symbol,
            "action": self.action.value,
            "eligibility": self.eligibility.value,
            "confidence_score": self.confidence_score,
            "heuristic_score": self.heuristic_score,
            "entry_plan": self.entry_plan.to_dict() if self.entry_plan else None,
            "risk_state": self.risk_state,
            "reasons": list(self.reasons),
            "warnings": list(self.warnings),
            "aggregate_state": self.aggregate_state.value if self.aggregate_state else None,
            "direction": self.direction.value if self.direction else None,
            "max_notional_usd": self.max_notional_usd,
            "sizing_details_json": self.sizing_details_json,
        }


@dataclass(frozen=True)
class DecisionJournalEntry:
    """Auditable journal entry for decision tracking."""
    decision_id: str
    cycle_id: str
    timestamp: datetime
    symbol: str
    action: DecisionAction
    eligibility: DecisionEligibility
    confidence_score: float
    entry_plan_json: str | None  # JSON-encoded entry plan
    reasons_json: str  # JSON-encoded reasons list
    warnings_json: str  # JSON-encoded warnings
    risk_state: str
    aggregate_state: StrategyState
    direction: HypothesisDirection | None
    heuristic_score: float
    max_notional_usd: float
    sizing_details_json: str | None  # JSON-encoded sizing info

    def to_dict(self) -> dict[str, Any]:
        """Serialize for database storage."""
        return {
            "decision_id": self.decision_id,
            "cycle_id": self.cycle_id,
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "action": self.action.value,
            "eligibility": self.eligibility.value,
            "confidence_score": self.confidence_score,
            "entry_plan_json": self.entry_plan_json,
            "reasons_json": self.reasons_json,
            "warnings_json": self.warnings_json,
            "risk_state": self.risk_state,
            "aggregate_state": self.aggregate_state.value,
            "direction": self.direction.value if self.direction else None,
            "heuristic_score": self.heuristic_score,
            "max_notional_usd": self.max_notional_usd,
            "sizing_details_json": self.sizing_details_json,
        }


@dataclass(frozen=True)
class DecisionOutcome:
    """Outcome tracking for executed decisions."""
    decision_id: str
    order_id: str | None
    filled: bool
    fill_price: float | None
    quantity: float | None
    notional: float | None  # Positive for buy, negative for sell
    fees_usd: float
    slippage_usd: float
    pnl_usd: float | None  # Unrealized/realized PnL
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "order_id": self.order_id,
            "filled": self.filled,
            "fill_price": self.fill_price,
            "quantity": self.quantity,
            "notional": self.notional,
            "fees_usd": self.fees_usd,
            "slippage_usd": self.slippage_usd,
            "pnl_usd": self.pnl_usd,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass(frozen=True)
class DecisionContext:
    """Full context for decision engine evaluation."""
    symbol: str
    aggregate_state: StrategyState  # Aggregate from aggregator (WATCH/WAIT/REJECT)
    direction: HypothesisDirection | None
    heuristic_score: float  # Raw aggregate score
    risk_state: str  # RiskState enum value
    max_notional_usd: float
    cash_available_usd: float
    portfolio_total_usd: float
    current_position_usd: float  # Current position value (0 if none)
    daily_loss_used_usd: float  # Daily loss guard usage
    daily_buy_remaining_usd: float  # Daily buy limit remaining
    volatility_score: float  # 0-1 scale
    market_price: float | None  # Current market price
    entry_price: float | None  # Average cost (for REDUCE decisions)