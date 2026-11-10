from __future__ import annotations

from dataclasses import dataclass

from app.market.binance_public import BinancePublicClient
from app.market.indicators import snapshot
from app.market.regime import detect_regime
from app.market.types import (
    MarketCandidate,
    MarketRegime,
    SUPPORTED_INTERVALS,
    SymbolInfo,
    Ticker24h,
    TimeframeAnalysis,
)


STABLE_BASES = {
    "USDT", "USDC", "FDUSD", "TUSD", "DAI", "USDP", "USDE", "PYUSD", "EUR", "AEUR",
}
LEVERAGED_SUFFIXES = ("UP", "DOWN", "BULL", "BEAR")
WRAPPED_BASES = {"WBTC", "WETH", "WBNB"}


@dataclass(frozen=True)
class ScannerConfig:
    quote_asset: str = "USDT"
    min_quote_volume_24h: float = 5_000_000.0
    min_trade_count_24h: int = 1_000
    min_candles: int = 120
    kline_limit: int = 250
    prefilter_limit: int = 30
    candidate_limit: int = 10


def is_allowed_symbol(info: SymbolInfo, quote: str = "USDT") -> bool:
    base = info.base_asset.upper()
    if info.quote_asset.upper() != quote.upper():
        return False
    if info.status != "TRADING" or not info.spot_allowed:
        return False
    if base in STABLE_BASES or base in WRAPPED_BASES:
        return False
    if base.endswith(LEVERAGED_SUFFIXES):
        return False
    return True


def passes_liquidity(ticker: Ticker24h, config: ScannerConfig) -> bool:
    return (
        ticker.last_price > 0
        and ticker.quote_volume >= config.min_quote_volume_24h
        and ticker.trade_count >= config.min_trade_count_24h
    )


def _rank_candidate(candidate: MarketCandidate) -> tuple[float, tuple[str, ...]]:
    score = 0.0
    reasons: list[str] = []
    analysis_4h = candidate.analysis_for("4h")
    analysis_1d = candidate.analysis_for("1d")
    analysis_1h = candidate.analysis_for("1h")

    regimes = [item.regime for item in candidate.analyses]
    directional = sum(regime in {MarketRegime.BULLISH, MarketRegime.BEARISH} for regime in regimes)
    score += directional * 8.0
    if directional >= 2:
        reasons.append("multi-timeframe directional structure")

    if analysis_4h and analysis_1d and analysis_4h.regime == analysis_1d.regime:
        if analysis_4h.regime in {MarketRegime.BULLISH, MarketRegime.BEARISH}:
            score += 22.0
            reasons.append("4h and 1d regimes agree")

    if analysis_1h:
        ratio = analysis_1h.indicators.volume_ratio
        if ratio >= 1.5:
            score += min(16.0, 8.0 + (ratio - 1.5) * 4.0)
            reasons.append("1h volume expansion")

    high_vol_count = sum(regime == MarketRegime.HIGH_VOLATILITY for regime in regimes)
    if high_vol_count:
        score -= high_vol_count * 8.0
        reasons.append("high volatility penalty")

    # Liquidity matters for candidate priority, but caps quickly so mega-caps do not dominate.
    liquidity_bonus = min(18.0, candidate.quote_volume_24h / 50_000_000.0 * 6.0)
    score += liquidity_bonus
    return max(0.0, min(100.0, score)), tuple(reasons)


class MarketScanner:
    def __init__(self, client: BinancePublicClient, config: ScannerConfig | None = None):
        self.client = client
        self.config = config or ScannerConfig()

    def prefilter(self) -> list[tuple[SymbolInfo, Ticker24h]]:
        infos = self.client.exchange_info()
        tickers = self.client.tickers_24h()
        pool: list[tuple[SymbolInfo, Ticker24h]] = []
        for info in infos:
            if not is_allowed_symbol(info, self.config.quote_asset):
                continue
            ticker = tickers.get(info.symbol)
            if ticker is None or not passes_liquidity(ticker, self.config):
                continue
            pool.append((info, ticker))
        pool.sort(key=lambda item: item[1].quote_volume, reverse=True)
        return pool[: self.config.prefilter_limit]

    def analyze_symbol(self, info: SymbolInfo, ticker: Ticker24h) -> MarketCandidate | None:
        analyses: list[TimeframeAnalysis] = []
        for interval in SUPPORTED_INTERVALS:
            candles = self.client.klines(info.symbol, interval, self.config.kline_limit)
            if len(candles) < self.config.min_candles:
                return None
            indicators = snapshot(candles)
            analyses.append(
                TimeframeAnalysis(
                    interval=interval,
                    candles=len(candles),
                    last_price=candles[-1].close,
                    indicators=indicators,
                    regime=detect_regime(indicators),
                )
            )

        candidate = MarketCandidate(
            symbol=info.symbol,
            base_asset=info.base_asset,
            quote_asset=info.quote_asset,
            quote_volume_24h=ticker.quote_volume,
            price_change_pct_24h=ticker.price_change_pct,
            trade_count_24h=ticker.trade_count,
            analyses=tuple(analyses),
        )
        score, reasons = _rank_candidate(candidate)
        return MarketCandidate(**{**candidate.__dict__, "ranking_score": score, "reasons": reasons})

    def scan(self) -> list[MarketCandidate]:
        candidates: list[MarketCandidate] = []
        for info, ticker in self.prefilter():
            candidate = self.analyze_symbol(info, ticker)
            if candidate is not None:
                candidates.append(candidate)
        candidates.sort(key=lambda item: (item.ranking_score, item.quote_volume_24h), reverse=True)
        return candidates[: self.config.candidate_limit]
