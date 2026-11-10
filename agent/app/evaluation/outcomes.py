from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from app.evaluation.historical import HistoricalPoint
from app.market.types import Candle, MarketRegime
from app.strategies.base import HypothesisDirection, StrategyState


DEFAULT_HORIZONS_MS: dict[str, int] = {
    "4h": 4 * 60 * 60 * 1000,
    "12h": 12 * 60 * 60 * 1000,
    "24h": 24 * 60 * 60 * 1000,
    "3d": 3 * 24 * 60 * 60 * 1000,
}


@dataclass(frozen=True)
class OutcomeWindow:
    horizon: str
    target_timestamp_ms: int
    observed_timestamp_ms: int
    exit_price: float
    raw_return_pct: float
    max_up_pct: float
    max_down_pct: float
    directional_return_pct: float | None
    mfe_pct: float | None
    mae_pct: float | None


@dataclass(frozen=True)
class OutcomeObservation:
    symbol: str
    source: str
    strategy: str | None
    state: StrategyState
    direction: HypothesisDirection | None
    score: float
    confidence: float
    signal_timestamp_ms: int
    entry_price: float
    market_regime: MarketRegime | None
    windows: tuple[OutcomeWindow, ...]

    def window_for(self, horizon: str) -> OutcomeWindow | None:
        return next((item for item in self.windows if item.horizon == horizon), None)


class OutcomeEvaluator:
    """Labels future market outcomes without simulating trades.

    Signal-time data comes from HistoricalPoint. Future labels are calculated only
    from candles whose close timestamp is strictly after the signal timestamp.
    This module does not size positions, apply fees, or create orders.
    """

    def __init__(
        self,
        *,
        outcome_interval: str = "1h",
        horizons_ms: Mapping[str, int] | None = None,
    ):
        self.outcome_interval = outcome_interval
        self.horizons_ms = dict(horizons_ms or DEFAULT_HORIZONS_MS)
        if not self.horizons_ms:
            raise ValueError("at least one outcome horizon is required")
        if any(value <= 0 for value in self.horizons_ms.values()):
            raise ValueError("outcome horizons must be positive")

    @staticmethod
    def _regime(point: HistoricalPoint) -> MarketRegime | None:
        analysis = point.candidate.analysis_for("4h") or point.candidate.analysis_for("1h")
        return analysis.regime if analysis else None

    @staticmethod
    def _directional_metrics(
        *,
        direction: HypothesisDirection | None,
        raw_return_pct: float,
        max_up_pct: float,
        max_down_pct: float,
    ) -> tuple[float | None, float | None, float | None]:
        if direction is HypothesisDirection.BUY:
            return raw_return_pct, max(max_up_pct, 0.0), max(-max_down_pct, 0.0)
        if direction is HypothesisDirection.SELL:
            return -raw_return_pct, max(-max_down_pct, 0.0), max(max_up_pct, 0.0)
        return None, None, None

    def _windows(
        self,
        *,
        point: HistoricalPoint,
        candles: Sequence[Candle],
        direction: HypothesisDirection | None,
    ) -> tuple[OutcomeWindow, ...]:
        analysis = point.candidate.analysis_for(self.outcome_interval)
        if analysis is None or analysis.last_price <= 0:
            return ()
        entry_price = analysis.last_price

        future = [
            candle
            for candle in candles
            if candle.close_time_ms > point.timestamp_ms
        ]
        if not future:
            return ()

        result: list[OutcomeWindow] = []
        for label, horizon_ms in self.horizons_ms.items():
            target_ms = point.timestamp_ms + horizon_ms
            target_index = next(
                (
                    index
                    for index, candle in enumerate(future)
                    if candle.close_time_ms >= target_ms
                ),
                None,
            )
            if target_index is None:
                continue

            observed = future[: target_index + 1]
            target = observed[-1]
            raw_return = (target.close / entry_price - 1.0) * 100.0
            max_up = (max(candle.high for candle in observed) / entry_price - 1.0) * 100.0
            max_down = (min(candle.low for candle in observed) / entry_price - 1.0) * 100.0
            directional_return, mfe, mae = self._directional_metrics(
                direction=direction,
                raw_return_pct=raw_return,
                max_up_pct=max_up,
                max_down_pct=max_down,
            )
            result.append(
                OutcomeWindow(
                    horizon=label,
                    target_timestamp_ms=target_ms,
                    observed_timestamp_ms=target.close_time_ms,
                    exit_price=target.close,
                    raw_return_pct=raw_return,
                    max_up_pct=max_up,
                    max_down_pct=max_down,
                    directional_return_pct=directional_return,
                    mfe_pct=mfe,
                    mae_pct=mae,
                )
            )
        return tuple(result)

    def evaluate_point(
        self,
        *,
        point: HistoricalPoint,
        candles_by_interval: Mapping[str, Sequence[Candle]],
    ) -> tuple[OutcomeObservation, ...]:
        candles = candles_by_interval.get(self.outcome_interval)
        if not candles:
            raise ValueError(f"missing outcome interval {self.outcome_interval}")

        analysis = point.candidate.analysis_for(self.outcome_interval)
        if analysis is None or analysis.last_price <= 0:
            return ()
        entry_price = analysis.last_price
        regime = self._regime(point)

        observations: list[OutcomeObservation] = []

        aggregate = point.aggregate
        observations.append(
            OutcomeObservation(
                symbol=point.candidate.symbol,
                source="aggregate",
                strategy=None,
                state=aggregate.state,
                direction=aggregate.direction,
                score=aggregate.score,
                confidence=aggregate.confidence,
                signal_timestamp_ms=point.timestamp_ms,
                entry_price=entry_price,
                market_regime=regime,
                windows=self._windows(
                    point=point,
                    candles=candles,
                    direction=aggregate.direction,
                ),
            )
        )

        for assessment in point.assessments:
            observations.append(
                OutcomeObservation(
                    symbol=assessment.symbol,
                    source="strategy",
                    strategy=assessment.strategy,
                    state=assessment.state,
                    direction=assessment.direction,
                    score=assessment.score,
                    confidence=assessment.confidence,
                    signal_timestamp_ms=point.timestamp_ms,
                    entry_price=entry_price,
                    market_regime=regime,
                    windows=self._windows(
                        point=point,
                        candles=candles,
                        direction=assessment.direction,
                    ),
                )
            )

        return tuple(observations)

    def evaluate_points(
        self,
        *,
        points: Sequence[HistoricalPoint],
        candles_by_interval: Mapping[str, Sequence[Candle]],
    ) -> tuple[OutcomeObservation, ...]:
        return tuple(
            observation
            for point in points
            for observation in self.evaluate_point(
                point=point,
                candles_by_interval=candles_by_interval,
            )
        )
