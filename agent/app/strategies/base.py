from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

from app.market.types import MarketCandidate


class StrategyState(str, Enum):
    WATCH = "WATCH"
    WAIT = "WAIT"
    REJECT = "REJECT"


class HypothesisDirection(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class StrategyAssessment:
    symbol: str
    strategy: str
    state: StrategyState
    direction: HypothesisDirection | None
    score: float
    confidence: float
    timeframe: str
    entry_low: float | None = None
    entry_high: float | None = None
    invalidation: float | None = None
    stop: float | None = None
    tp1: float | None = None
    tp2: float | None = None
    risk_reward: float | None = None
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not 0 <= self.score <= 100:
            raise ValueError("score must be between 0 and 100")
        if not 0 <= self.confidence <= 100:
            raise ValueError("confidence must be between 0 and 100")
        if self.state is StrategyState.REJECT and self.direction is not None:
            raise ValueError("rejected assessments cannot carry a direction")


class Strategy(Protocol):
    name: str

    def evaluate(self, candidate: MarketCandidate) -> StrategyAssessment: ...
