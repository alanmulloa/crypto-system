from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


SUPPORTED_INTERVALS = ("15m", "1h", "4h", "1d")


class MarketRegime(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"


@dataclass(frozen=True)
class SymbolInfo:
    symbol: str
    base_asset: str
    quote_asset: str
    status: str
    spot_allowed: bool = True


@dataclass(frozen=True)
class Ticker24h:
    symbol: str
    last_price: float
    quote_volume: float
    price_change_pct: float
    trade_count: int = 0


@dataclass(frozen=True)
class Candle:
    open_time_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time_ms: int
    quote_volume: float = 0.0
    trades: int = 0


@dataclass(frozen=True)
class IndicatorSnapshot:
    ema_fast: float
    ema_slow: float
    rsi: float
    atr: float
    atr_pct: float
    volume_ratio: float
    structure: str


@dataclass(frozen=True)
class TimeframeAnalysis:
    interval: str
    candles: int
    last_price: float
    indicators: IndicatorSnapshot
    regime: MarketRegime


@dataclass(frozen=True)
class MarketCandidate:
    symbol: str
    base_asset: str
    quote_asset: str
    quote_volume_24h: float
    price_change_pct_24h: float
    trade_count_24h: int
    analyses: tuple[TimeframeAnalysis, ...] = field(default_factory=tuple)
    ranking_score: float = 0.0
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def analysis_for(self, interval: str) -> TimeframeAnalysis | None:
        return next((item for item in self.analyses if item.interval == interval), None)


def closes(candles: Iterable[Candle]) -> list[float]:
    return [c.close for c in candles]
