from __future__ import annotations

from app.market.types import MarketCandidate, MarketRegime
from app.strategies.base import HypothesisDirection, StrategyAssessment, StrategyState
from app.strategies.common import analysis, assessment, rejection


class PullbackStrategy:
    name = "pullback"

    def evaluate(self, candidate: MarketCandidate) -> StrategyAssessment:
        h1 = analysis(candidate, "1h")
        h4 = analysis(candidate, "4h")
        d1 = analysis(candidate, "1d")
        if not h1 or not h4 or not d1:
            return rejection(candidate.symbol, self.name, "1h, 4h and 1d context required")

        if h4.regime == d1.regime == MarketRegime.BULLISH:
            direction = HypothesisDirection.BUY
            rsi_ok = 38 <= h1.indicators.rsi <= 58
        elif h4.regime == d1.regime == MarketRegime.BEARISH:
            direction = HypothesisDirection.SELL
            rsi_ok = 42 <= h1.indicators.rsi <= 62
        else:
            return rejection(candidate.symbol, self.name, "higher timeframes do not define one trend")

        distance = abs(h1.last_price - h1.indicators.ema_fast)
        near_fast_ema = distance <= max(h1.indicators.atr * 0.8, h1.last_price * 0.002)
        if not near_fast_ema:
            return StrategyAssessment(
                symbol=candidate.symbol,
                strategy=self.name,
                state=StrategyState.WAIT,
                direction=direction,
                score=45,
                confidence=45,
                timeframe="1h+4h+1d",
                reasons=("higher-timeframe trend exists", "price has not pulled back near 1h EMA20"),
            )

        score = 62.0
        reasons = ["higher-timeframe trend exists", "price is near 1h EMA20"]
        if rsi_ok:
            score += 14
            reasons.append("1h RSI is consistent with a pullback")
        if h1.indicators.volume_ratio < 1.4:
            score += 8
            reasons.append("pullback is not accompanied by volume expansion")
        if h4.indicators.structure != "mixed":
            score += 8
            reasons.append("4h market structure remains directional")

        confidence = min(88.0, 48.0 + score * 0.4)
        return assessment(
            candidate=candidate,
            strategy=self.name,
            state=StrategyState.WATCH if score >= 72 else StrategyState.WAIT,
            direction=direction,
            score=score,
            confidence=confidence,
            timeframe="1h+4h+1d",
            price=h1.last_price,
            atr=h1.indicators.atr,
            reasons=reasons,
            stop_atr=1.3,
        )
