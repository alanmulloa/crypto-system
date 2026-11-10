from enum import Enum
from pydantic import BaseModel, Field


class Decision(str, Enum):
    TRADE = "TRADE"
    WATCH = "WATCH"
    WAIT = "WAIT"
    REJECT = "REJECT"


class Direction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class StrategySignal(BaseModel):
    symbol: str
    strategy: str
    direction: Direction
    score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=100)
    entry_low: float | None = None
    entry_high: float | None = None
    stop: float | None = None
    tp1: float | None = None
    tp2: float | None = None
    risk_reward: float | None = None
    reasons: list[str] = Field(default_factory=list)


class RiskDecision(BaseModel):
    approved: bool
    max_notional_usd: float = 0
    reasons: list[str] = Field(default_factory=list)
