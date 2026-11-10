from __future__ import annotations

from app.market.types import IndicatorSnapshot, MarketRegime


def detect_regime(indicators: IndicatorSnapshot, *, high_volatility_atr_pct: float = 4.5) -> MarketRegime:
    if indicators.atr_pct >= high_volatility_atr_pct:
        return MarketRegime.HIGH_VOLATILITY

    bullish_structure = indicators.structure == "higher_highs_higher_lows"
    bearish_structure = indicators.structure == "lower_highs_lower_lows"

    if indicators.ema_fast > indicators.ema_slow and indicators.rsi >= 52 and bullish_structure:
        return MarketRegime.BULLISH
    if indicators.ema_fast < indicators.ema_slow and indicators.rsi <= 48 and bearish_structure:
        return MarketRegime.BEARISH
    return MarketRegime.RANGING
