from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from app.market.indicators import snapshot
from app.market.regime import detect_regime
from app.market.types import Candle, MarketCandidate, TimeframeAnalysis
from app.strategies.aggregator import AggregatedAssessment, StrategyAggregator
from app.strategies.base import StrategyAssessment
from app.strategies.engine import StrategyEngine


@dataclass(frozen=True)
class HistoricalPoint:
    timestamp_ms: int
    candidate: MarketCandidate
    assessments: tuple[StrategyAssessment, ...]
    aggregate: AggregatedAssessment


class HistoricalSanityRunner:
    """Walk-forward evaluator for strategy sanity checks.

    At every historical point, only candles whose close timestamp is <= the point
    timestamp are visible. This class is deliberately not a backtest broker and
    does not simulate fills, PnL, or position sizing.
    """

    def __init__(
        self,
        strategy_engine: StrategyEngine | None = None,
        aggregator: StrategyAggregator | None = None,
        *,
        min_candles: int = 60,
    ):
        if min_candles < 50:
            raise ValueError("min_candles must be at least 50 for current indicators")
        self.strategy_engine = strategy_engine or StrategyEngine()
        self.aggregator = aggregator or StrategyAggregator()
        self.min_candles = min_candles

    def build_candidate(
        self,
        *,
        symbol: str,
        base_asset: str,
        quote_asset: str,
        candles_by_interval: Mapping[str, Sequence[Candle]],
        timestamp_ms: int,
    ) -> MarketCandidate | None:
        analyses: list[TimeframeAnalysis] = []

        for interval in ("15m", "1h", "4h", "1d"):
            source = candles_by_interval.get(interval)
            if not source:
                return None
            visible = [candle for candle in source if candle.close_time_ms <= timestamp_ms]
            if len(visible) < self.min_candles:
                return None

            indicators = snapshot(visible)
            analyses.append(
                TimeframeAnalysis(
                    interval=interval,
                    candles=len(visible),
                    last_price=visible[-1].close,
                    indicators=indicators,
                    regime=detect_regime(indicators),
                )
            )

        return MarketCandidate(
            symbol=symbol,
            base_asset=base_asset,
            quote_asset=quote_asset,
            quote_volume_24h=0.0,
            price_change_pct_24h=0.0,
            trade_count_24h=0,
            analyses=tuple(analyses),
            ranking_score=0.0,
            reasons=("historical_sanity",),
        )

    def run(
        self,
        *,
        symbol: str,
        base_asset: str,
        quote_asset: str,
        candles_by_interval: Mapping[str, Sequence[Candle]],
        anchor_interval: str = "1h",
        max_points: int | None = None,
    ) -> tuple[HistoricalPoint, ...]:
        anchor = candles_by_interval.get(anchor_interval)
        if not anchor:
            raise ValueError(f"missing anchor interval {anchor_interval}")

        timestamps = [candle.close_time_ms for candle in anchor]
        if max_points is not None:
            if max_points <= 0:
                raise ValueError("max_points must be positive")
            timestamps = timestamps[-max_points:]

        points: list[HistoricalPoint] = []
        for timestamp_ms in timestamps:
            candidate = self.build_candidate(
                symbol=symbol,
                base_asset=base_asset,
                quote_asset=quote_asset,
                candles_by_interval=candles_by_interval,
                timestamp_ms=timestamp_ms,
            )
            if candidate is None:
                continue
            assessments = self.strategy_engine.evaluate(candidate)
            aggregate = self.aggregator.aggregate(assessments)
            points.append(
                HistoricalPoint(
                    timestamp_ms=timestamp_ms,
                    candidate=candidate,
                    assessments=assessments,
                    aggregate=aggregate,
                )
            )
        return tuple(points)
