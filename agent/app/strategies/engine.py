from __future__ import annotations

from collections.abc import Iterable

from app.market.types import MarketCandidate
from app.strategies.base import Strategy, StrategyAssessment
from app.strategies.breakout import BreakoutStrategy
from app.strategies.mean_reversion import MeanReversionStrategy
from app.strategies.momentum import MomentumStrategy
from app.strategies.pullback import PullbackStrategy
from app.strategies.trend import TrendFollowingStrategy


DEFAULT_STRATEGIES: tuple[Strategy, ...] = (
    TrendFollowingStrategy(),
    PullbackStrategy(),
    BreakoutStrategy(),
    MeanReversionStrategy(),
    MomentumStrategy(),
)


class StrategyEngine:
    """Phase 2A evaluator only.

    It compares independent strategy hypotheses. It does not aggregate them into a
    trade decision, call the Risk Manager, or access any broker/execution module.
    """

    def __init__(self, strategies: Iterable[Strategy] | None = None):
        self.strategies = tuple(strategies or DEFAULT_STRATEGIES)

    def evaluate(self, candidate: MarketCandidate) -> tuple[StrategyAssessment, ...]:
        return tuple(strategy.evaluate(candidate) for strategy in self.strategies)
