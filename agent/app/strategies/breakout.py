from __future__ import annotations

from app.market.types import MarketCandidate, MarketRegime
from app.strategies.base import HypothesisDirection, StrategyAssessment, StrategyState
from app.strategies.common import analysis, assessment, rejection


class BreakoutStrategy:
    name = "breakout"

    def evaluate(self, candidate: MarketCandidate) -> StrategyAssessment:
        h1 = analysis(candidate, "1h")
        h4 = analysis(candidate, "4h")
        if not h1 or not h4:
            return rejection(candidate.symbol, self.name, "1h and 4h context required")

        bullish = (
            h1.indicators.structure == "higher_highs_higher_lows"
            and h1.indicators.ema_fast > h1.indicators.ema_slow
        )
        bearish = (
            h1.indicators.structure == "lower_highs_lower_lows"
            and h1.indicators.ema_fast < h1.indicators.ema_slow
        )
        if bullish:
            direction = HypothesisDirection.BUY
        elif bearish:
            direction = HypothesisDirection.SELL
        else:
            return rejection(candidate.symbol, self.name, "1h structure is not breaking directionally")

        if h1.indicators.volume_ratio < 1.35:
            return StrategyAssessment(
                symbol=candidate.symbol,
                strategy=self.name,
                state=StrategyState.WAIT,
                direction=direction,
                score=48,
                confidence=42,
                timeframe="1h+4h",
                reasons=("directional 1h structure detected", "breakout lacks volume confirmation"),
            )

        score = 70.0
        reasons = ["directional 1h structure detected", "1h volume expansion confirms breakout"]
        if h4.regime in {MarketRegime.BULLISH, MarketRegime.BEARISH}:
            expected = MarketRegime.BULLISH if direction is HypothesisDirection.BUY else MarketRegime.BEARISH
            if h4.regime == expected:
                score += 14
                reasons.append("4h regime confirms breakout direction")
        if h1.indicators.atr_pct < 4.5:
            score += 6
            reasons.append("volatility is below extreme regime threshold")

        confidence = min(90.0, 52.0 + score * 0.38)
        return assessment(
            candidate=candidate,
            strategy=self.name,
            state=StrategyState.WATCH if score >= 75 else StrategyState.WAIT,
            direction=direction,
            score=score,
            confidence=confidence,
            timeframe="1h+4h",
            price=h1.last_price,
            atr=h1.indicators.atr,
            reasons=reasons,
            stop_atr=1.4,
        )
