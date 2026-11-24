"""B9: Decision Engine eligibility fail-closed tests.

Tests that WATCH/PASS_RESEARCH states without explicit PAPER_PROPOSAL eligibility
cannot authorize execution. RESEARCH_ONLY and BLOCKED must block all trades.
"""
from app.decision.eligibility import determine_action, evaluate_eligibility
from app.decision.models import DecisionEligibility
from app.risk.portfolio import RiskState
from app.strategies.aggregator import AggregatedAssessment
from app.strategies.base import HypothesisDirection, StrategyState


def make_aggregate(
    *,
    state=StrategyState.WATCH,
    direction=HypothesisDirection.BUY,
    symbol="BTCUSDT",
):
    return AggregatedAssessment(
        symbol=symbol,
        state=state,
        direction=direction,
        score=80.0,
        confidence=75.0,
        supporting_strategies=("momentum",),
        conflicting_strategies=(),
        rejected_strategies=(),
        reasons=(),
    )


class TestEligibilityFailClosed:
    """Eligibility gates must block execution unless explicitly PAPER_PROPOSAL."""

    def test_research_only_when_wait_state(self):
        """WAIT state returns RESEARCH_ONLY, not PAPER_PROPOSAL."""
        assessment = make_aggregate(state=StrategyState.WAIT)
        eligibility = evaluate_eligibility(
            assessment=assessment,
            risk_state=RiskState.APPROVED,
            risk_approved=True,
            max_notional_usd=100.0,
        )
        assert eligibility is DecisionEligibility.RESEARCH_ONLY
        action, _ = determine_action(
            assessment, eligibility, current_position_usd=50.0, requested_notional_usd=100.0
        )
        assert action == "NO_ACTION"

    def test_research_only_when_reject_state(self):
        """REJECT state returns RESEARCH_ONLY, not PAPER_PROPOSAL."""
        assessment = make_aggregate(state=StrategyState.REJECT, direction=None)
        eligibility = evaluate_eligibility(
            assessment=assessment,
            risk_state=RiskState.APPROVED,
            risk_approved=True,
            max_notional_usd=100.0,
        )
        assert eligibility is DecisionEligibility.RESEARCH_ONLY
        action, _ = determine_action(
            assessment, eligibility, current_position_usd=50.0, requested_notional_usd=100.0
        )
        assert action == "NO_ACTION"

    def test_blocked_when_risk_not_approved(self):
        """Risk BLOCKED state returns BLOCKED, not PAPER_PROPOSAL."""
        assessment = make_aggregate(state=StrategyState.WATCH)
        eligibility = evaluate_eligibility(
            assessment=assessment,
            risk_state=RiskState.BLOCKED,
            risk_approved=False,
            max_notional_usd=0.0,
        )
        assert eligibility is DecisionEligibility.BLOCKED
        action, _ = determine_action(
            assessment, eligibility, current_position_usd=50.0, requested_notional_usd=100.0
        )
        assert action == "NO_ACTION"

    def test_blocked_when_no_notional_capacity(self):
        """Zero max_notional blocks even WATCH state."""
        assessment = make_aggregate(state=StrategyState.WATCH)
        eligibility = evaluate_eligibility(
            assessment=assessment,
            risk_state=RiskState.APPROVED,
            risk_approved=True,
            max_notional_usd=0.0,
        )
        assert eligibility is DecisionEligibility.BLOCKED
        action, _ = determine_action(
            assessment, eligibility, current_position_usd=50.0, requested_notional_usd=100.0
        )
        assert action == "NO_ACTION"

    def test_paper_proposal_requires_watch_and_approved_risk(self):
        """WATCH + APPROVED risk + positive notional = PAPER_PROPOSAL only."""
        assessment = make_aggregate(state=StrategyState.WATCH)
        eligibility = evaluate_eligibility(
            assessment=assessment,
            risk_state=RiskState.APPROVED,
            risk_approved=True,
            max_notional_usd=100.0,
        )
        assert eligibility is DecisionEligibility.PAPER_PROPOSAL
        action, _ = determine_action(
            assessment, eligibility, current_position_usd=50.0, requested_notional_usd=100.0
        )
        assert action == "BUY"

    def test_sell_without_position_is_blocked(self):
        """SELL direction with zero current position = BLOCKED."""
        assessment = make_aggregate(
            state=StrategyState.WATCH, direction=HypothesisDirection.SELL
        )
        eligibility = evaluate_eligibility(
            assessment=assessment,
            risk_state=RiskState.APPROVED,
            risk_approved=True,
            max_notional_usd=100.0,
            current_position_usd=0.0,
        )
        assert eligibility is DecisionEligibility.BLOCKED

    def test_sell_with_position_is_paper_proposal(self):
        """SELL direction with existing position = PAPER_PROPOSAL."""
        assessment = make_aggregate(
            state=StrategyState.WATCH, direction=HypothesisDirection.SELL
        )
        eligibility = evaluate_eligibility(
            assessment=assessment,
            risk_state=RiskState.APPROVED,
            risk_approved=True,
            max_notional_usd=100.0,
            current_position_usd=50.0,
        )
        assert eligibility is DecisionEligibility.PAPER_PROPOSAL
        action, _ = determine_action(
            assessment, eligibility, current_position_usd=50.0, requested_notional_usd=100.0
        )
        assert action in ("SELL", "REDUCE")

    def test_no_action_when_risk_approved_but_direction_none(self):
        """WATCH with direction=None is RESEARCH_ONLY, not PAPER_PROPOSAL."""
        assessment = make_aggregate(state=StrategyState.WATCH, direction=None)
        eligibility = evaluate_eligibility(
            assessment=assessment,
            risk_state=RiskState.APPROVED,
            risk_approved=True,
            max_notional_usd=100.0,
        )
        assert eligibility is DecisionEligibility.RESEARCH_ONLY
        action, _ = determine_action(
            assessment, eligibility, current_position_usd=50.0, requested_notional_usd=100.0
        )
        assert action == "NO_ACTION"


class TestEligibilityNoImplicitAuthorization:
    """Verify no implicit authorization from WATCH or risk_approved alone."""

    def test_watch_alone_does_not_authorize(self):
        """WATCH state alone is not enough — need all conditions."""
        assessment_wait = make_aggregate(state=StrategyState.WAIT)
        eligibility = evaluate_eligibility(
            assessment=assessment_wait,
            risk_state=RiskState.APPROVED,
            risk_approved=True,
            max_notional_usd=100.0,
        )
        assert eligibility is not DecisionEligibility.PAPER_PROPOSAL

    def test_risk_approved_alone_does_not_authorize(self):
        """risk_approved=True without WATCH state is not enough."""
        assessment = make_aggregate(state=StrategyState.REJECT, direction=None)
        eligibility = evaluate_eligibility(
            assessment=assessment,
            risk_state=RiskState.APPROVED,
            risk_approved=True,
            max_notional_usd=100.0,
        )
        assert eligibility is not DecisionEligibility.PAPER_PROPOSAL

    def test_notional_alone_does_not_authorize(self):
        """max_notional > 0 without WATCH + approved risk is not enough."""
        assessment = make_aggregate(state=StrategyState.WAIT)
        eligibility = evaluate_eligibility(
            assessment=assessment,
            risk_state=RiskState.APPROVED,
            risk_approved=True,
            max_notional_usd=500.0,
        )
        assert eligibility is not DecisionEligibility.PAPER_PROPOSAL
