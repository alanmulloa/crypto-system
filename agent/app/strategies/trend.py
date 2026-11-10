from __future__ import annotations

from app.market.types import MarketCandidate, MarketRegime
from app.strategies.base import HypothesisDirection, StrategyAssessment, StrategyState
from app.strategies.common import analysis, assessment, rejection


class TrendFollowingStrategy:
    name = "trend_following"

    def evaluate(self, candidate: MarketCandidate) -> StrategyAssessment:
        h4 = analysis(candidate, "4h")
        d1 = analysis(candidate, "1d")
        if not h4 or not d1:
            return rejection(candidate.symbol, self.name, "4h and 1d context required")

        if h4.regime == d1.regime == MarketRegime.BULLISH:
            direction = HypothesisDirection.BUY
            structure_ok = h4.indicators.structure == "higher_highs_higher_lows"
        elif h4.regime == d1.regime == MarketRegime.BEARISH:
            direction = HypothesisDirection.SELL
            structure_ok = h4.indicators.structure == "lower_highs_lower_lows"
        else:
            return rejection(candidate.symbol, self.name, "4h and 1d trend regimes do not agree")

        score = 68.0
        reasons = ["4h and 1d directional regimes agree"]
        if structure_ok:
            score += 12
            reasons.append("4h structure confirms trend")
        if 45 <= h4.indicators.rsi <= 72:
            score += 8
            reasons.append("4h RSI is not extreme")
        if h4.indicators.volume_ratio >= 1.1:
            score += 7
            reasons.append("4h volume supports trend")

        confidence = min(90.0, 55.0 + score * 0.35)
        state = StrategyState.WATCH if score >= 75 else StrategyState.WAIT
        return assessment(
            candidate=candidate,
            strategy=self.name,
            state=state,
            direction=direction,
            score=score,
            confidence=confidence,
            timeframe="4h+1d",
            price=h4.last_price,
            atr=h4.indicators.atr,
            reasons=reasons,
            stop_atr=1.5,
        )
