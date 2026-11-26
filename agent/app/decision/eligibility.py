"""Eligibility gates for trading decisions.

Phase 2: Determines whether a decision can proceed to paper trading or is
restricted to RESEARCH_ONLY/BLOCKED.
"""
from __future__ import annotations

from app.decision.models import DecisionEligibility
from app.risk.portfolio import RiskState
from app.strategies.aggregator import AggregatedAssessment
from app.strategies.base import HypothesisDirection, StrategyState


def evaluate_eligibility(
    assessment: AggregatedAssessment,
    risk_state: RiskState,
    risk_approved: bool,
    max_notional_usd: float,
    current_position_usd: float = 0.0,
) -> DecisionEligibility:
    """Evaluate trading eligibility based on aggregate state, risk, and position.

    Rules:
    1. If aggregate state is WAIT or REJECT -> RESEARCH_ONLY (signal exists but no action)
    2. If risk is BLOCKED -> BLOCKED
    3. If risk approved but no actionable notional -> BLOCKED
    4. If WATCH with BUY/SELL and approved -> PAPER_PROPOSAL
    5. REDUCE (partial sell) requires existing position -> PAPER_PROPOSAL if position > 0

    Args:
        assessment: Aggregated strategy assessment
        risk_state: Portfolio risk state (APPROVED/BLOCKED/NO_ACTION)
        risk_approved: Whether risk check passed
        max_notional_usd: Maximum notional available for this action
        current_position_usd: Current position value (for SELL/REDUCE)

    Returns:
        DecisionEligibility enum value
    """
    # WAIT or REJECT = research signal only, no trading
    if assessment.state in (StrategyState.WAIT, StrategyState.REJECT):
        return DecisionEligibility.RESEARCH_ONLY

    # Risk blocked
    if risk_state is RiskState.BLOCKED or not risk_approved:
        return DecisionEligibility.BLOCKED

    # No actionable notional
    if max_notional_usd <= 0:
        return DecisionEligibility.BLOCKED

    # For SELL/REDUCE, must have existing position
    if assessment.direction in (HypothesisDirection.SELL,) and current_position_usd <= 0:
        return DecisionEligibility.BLOCKED

    # WATCH with actionable direction and approved risk = paper proposal
    if assessment.state is StrategyState.WATCH and assessment.direction is not None:
        return DecisionEligibility.PAPER_PROPOSAL

    # Default: research only
    return DecisionEligibility.RESEARCH_ONLY


def determine_action(
    assessment: AggregatedAssessment,
    eligibility: DecisionEligibility,
    current_position_usd: float = 0.0,
    requested_notional_usd: float = 0.0,
) -> tuple[str, str]:
    """Determine the decision action from eligibility and assessment.

    Returns:
        Tuple of (action_str, reason_str)
    """
    if eligibility is DecisionEligibility.RESEARCH_ONLY:
        if assessment.state is StrategyState.WAIT:
            return ("NO_ACTION", "aggregate state is WAIT - awaiting confirmation")
        elif assessment.state is StrategyState.REJECT:
            return ("NO_ACTION", "aggregate state is REJECT - conflicting signals")
        return ("NO_ACTION", "research signal only")

    if eligibility is DecisionEligibility.BLOCKED:
        return ("NO_ACTION", "blocked by risk constraints")

    # PAPER_PROPOSAL: determine specific action
    if assessment.direction is HypothesisDirection.BUY:
        return ("BUY", "bullish signal with approved risk")

    if assessment.direction is HypothesisDirection.SELL:
        if current_position_usd > 0:
            # Full sell or partial reduce based on requested notional
            if requested_notional_usd >= current_position_usd * 0.9:
                return ("SELL", "bearish signal - full position exit")
            else:
                return ("REDUCE", "bearish signal - partial position reduction")
        return ("NO_ACTION", "sell signal but no position held")

    return ("NO_ACTION", "no actionable direction")