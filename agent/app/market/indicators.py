from __future__ import annotations

from statistics import fmean

from app.market.types import Candle, IndicatorSnapshot


def ema(values: list[float], period: int) -> float:
    if period <= 0:
        raise ValueError("period must be positive")
    if len(values) < period:
        raise ValueError(f"need at least {period} values")
    seed = fmean(values[:period])
    multiplier = 2.0 / (period + 1.0)
    current = seed
    for value in values[period:]:
        current = (value - current) * multiplier + current
    return current


def rsi(values: list[float], period: int = 14) -> float:
    if len(values) <= period:
        raise ValueError(f"need more than {period} values")
    changes = [values[i] - values[i - 1] for i in range(1, len(values))]
    gains = [max(change, 0.0) for change in changes]
    losses = [max(-change, 0.0) for change in changes]
    avg_gain = fmean(gains[:period])
    avg_loss = fmean(losses[:period])
    for gain, loss in zip(gains[period:], losses[period:]):
        avg_gain = ((avg_gain * (period - 1)) + gain) / period
        avg_loss = ((avg_loss * (period - 1)) + loss) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def atr(candles: list[Candle], period: int = 14) -> float:
    if len(candles) <= period:
        raise ValueError(f"need more than {period} candles")
    true_ranges: list[float] = []
    for i in range(1, len(candles)):
        current = candles[i]
        previous = candles[i - 1]
        true_ranges.append(
            max(
                current.high - current.low,
                abs(current.high - previous.close),
                abs(current.low - previous.close),
            )
        )
    current_atr = fmean(true_ranges[:period])
    for value in true_ranges[period:]:
        current_atr = ((current_atr * (period - 1)) + value) / period
    return current_atr


def volume_ratio(candles: list[Candle], lookback: int = 20) -> float:
    if len(candles) < lookback + 1:
        raise ValueError(f"need at least {lookback + 1} candles")
    previous = [c.volume for c in candles[-(lookback + 1):-1]]
    baseline = fmean(previous)
    return candles[-1].volume / baseline if baseline > 0 else 0.0


def market_structure(candles: list[Candle], lookback: int = 20) -> str:
    if len(candles) < lookback:
        raise ValueError(f"need at least {lookback} candles")
    window = candles[-lookback:]
    half = max(2, lookback // 2)
    older = window[:half]
    newer = window[half:]
    older_high = max(c.high for c in older)
    older_low = min(c.low for c in older)
    newer_high = max(c.high for c in newer)
    newer_low = min(c.low for c in newer)
    if newer_high > older_high and newer_low > older_low:
        return "higher_highs_higher_lows"
    if newer_high < older_high and newer_low < older_low:
        return "lower_highs_lower_lows"
    return "mixed"


def snapshot(candles: list[Candle], fast_period: int = 20, slow_period: int = 50) -> IndicatorSnapshot:
    minimum = max(slow_period, 21)
    if len(candles) < minimum:
        raise ValueError(f"need at least {minimum} candles")
    close_values = [c.close for c in candles]
    last_price = close_values[-1]
    atr_value = atr(candles, 14)
    return IndicatorSnapshot(
        ema_fast=ema(close_values, fast_period),
        ema_slow=ema(close_values, slow_period),
        rsi=rsi(close_values, 14),
        atr=atr_value,
        atr_pct=(atr_value / last_price * 100.0) if last_price else 0.0,
        volume_ratio=volume_ratio(candles, 20),
        structure=market_structure(candles, 20),
    )
