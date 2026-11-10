from __future__ import annotations

from app.market.types import MarketCandidate, TimeframeAnalysis
from app.strategies.base import HypothesisDirection, StrategyAssessment, StrategyState


def analysis(candidate: MarketCandidate, interval: str) -> TimeframeAnalysis | None:
    return candidate.analysis_for(interval)


def rejection(symbol: str, strategy: str, reason: str, timeframe: str = "multi") -> StrategyAssessment:
    return StrategyAssessment(
        symbol=symbol,
        strategy=strategy,
        state=StrategyState.REJECT,
        direction=None,
        score=0,
        confidence=0,
        timeframe=timeframe,
        reasons=(reason,),
    )


def levels(
    price: float,
    atr: float,
    direction: HypothesisDirection,
    *,
    stop_atr: float = 1.2,
    tp1_r: float = 1.5,
    tp2_r: float = 2.5,
) -> tuple[float, float, float, float, float, float]:
    if price <= 0 or atr <= 0:
        raise ValueError("price and atr must be positive")
    risk = atr * stop_atr
    entry_low = max(0.0, price - atr * 0.15)
    entry_high = price + atr * 0.15
    if direction is HypothesisDirection.BUY:
        stop = max(0.0, price - risk)
        tp1 = price + risk * tp1_r
        tp2 = price + risk * tp2_r
        invalidation = stop
    else:
        stop = price + risk
        tp1 = max(0.0, price - risk * tp1_r)
        tp2 = max(0.0, price - risk * tp2_r)
        invalidation = stop
    return entry_low, entry_high, invalidation, stop, tp1, tp2


def assessment(
    *,
    candidate: MarketCandidate,
    strategy: str,
    state: StrategyState,
    direction: HypothesisDirection,
    score: float,
    confidence: float,
    timeframe: str,
    price: float,
    atr: float,
    reasons: list[str],
    stop_atr: float = 1.2,
) -> StrategyAssessment:
    entry_low, entry_high, invalidation, stop, tp1, tp2 = levels(
        price,
        atr,
        direction,
        stop_atr=stop_atr,
    )
    risk = abs(price - stop)
    reward = abs(tp2 - price)
    return StrategyAssessment(
        symbol=candidate.symbol,
        strategy=strategy,
        state=state,
        direction=direction,
        score=max(0.0, min(100.0, score)),
        confidence=max(0.0, min(100.0, confidence)),
        timeframe=timeframe,
        entry_low=entry_low,
        entry_high=entry_high,
        invalidation=invalidation,
        stop=stop,
        tp1=tp1,
        tp2=tp2,
        risk_reward=(reward / risk) if risk else None,
        reasons=tuple(reasons),
    )
