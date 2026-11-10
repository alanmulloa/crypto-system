from __future__ import annotations

from app.market.types import MarketCandidate, MarketRegime
from app.strategies.base import HypothesisDirection, StrategyAssessment, StrategyState
from app.strategies.common import analysis, assessment, rejection


class MeanReversionStrategy:
    name = "mean_reversion"

    def evaluate(self, candidate: MarketCandidate) -> StrategyAssessment:
        h1 = analysis(candidate, "1h")
        h4 = analysis(candidate, "4h")
        if not h1 or not h4:
            return rejection(candidate.symbol, self.name, "1h and 4h context required")

        if h4.regime != MarketRegime.RANGING:
            return rejection(candidate.symbol, self.name, "4h market is not ranging")

        if h1.indicators.rsi <= 35:
            direction = HypothesisDirection.BUY
            stretched = h1.last_price < h1.indicators.ema_fast
        elif h1.indicators.rsi >= 65:
            direction = HypothesisDirection.SELL
            stretched = h1.last_price > h1.indicators.ema_fast
        else:
            return rejection(candidate.symbol, self.name, "1h RSI is not stretched enough")

        score = 60.0
        reasons = ["4h regime is ranging", "1h RSI is stretched"]
        if stretched:
            score += 14
            reasons.append("price is stretched away from 1h EMA20")
        if h1.indicators.volume_ratio <= 1.5:
            score += 7
            reasons.append("no extreme volume expansion against mean reversion")
        if h1.indicators.atr_pct < 4.5:
            score += 7
            reasons.append("volatility is not extreme")

        confidence = min(85.0, 45.0 + score * 0.4)
        return assessment(
            candidate=candidate,
            strategy=self.name,
            state=StrategyState.WATCH if score >= 72 else StrategyState.WAIT,
            direction=direction,
            score=score,
            confidence=confidence,
            timeframe="1h+4h",
            price=h1.last_price,
            atr=h1.indicators.atr,
            reasons=reasons,
            stop_atr=1.1,
        )
