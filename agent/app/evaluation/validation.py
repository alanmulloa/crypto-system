from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from statistics import fmean
from typing import Mapping, Sequence

from app.evaluation.backtest import BacktestReport, BacktestSimulator
from app.evaluation.historical import HistoricalPoint
from app.evaluation.outcome_metrics import OutcomeSummary, summarize_outcomes
from app.evaluation.outcomes import OutcomeEvaluator, OutcomeObservation
from app.market.types import Candle
from app.strategies.base import StrategyState


class ValidationSegment(str, Enum):
    CALIBRATION = "calibration"
    VALIDATION = "validation"
    OUT_OF_SAMPLE = "out_of_sample"


@dataclass(frozen=True)
class TemporalSplitConfig:
    calibration_ratio: float = 0.60
    validation_ratio: float = 0.20
    out_of_sample_ratio: float = 0.20
    min_points_per_segment: int = 20

    def __post_init__(self) -> None:
        ratios = (
            self.calibration_ratio,
            self.validation_ratio,
            self.out_of_sample_ratio,
        )
        if any(value <= 0 for value in ratios):
            raise ValueError("all temporal split ratios must be positive")
        if abs(sum(ratios) - 1.0) > 1e-9:
            raise ValueError("temporal split ratios must sum to 1")
        if self.min_points_per_segment <= 0:
            raise ValueError("min_points_per_segment must be positive")


@dataclass(frozen=True)
class RegimePerformance:
    regime: str
    trades: int
    net_pnl_usd: float
    expectancy_usd: float | None
    win_rate_pct: float | None


@dataclass(frozen=True)
class ScoreThresholdSensitivity:
    threshold: float
    observations: int
    avg_directional_return_pct: float | None
    directional_hit_rate_pct: float | None


@dataclass(frozen=True)
class SegmentValidation:
    segment: ValidationSegment
    start_timestamp_ms: int
    end_timestamp_ms: int
    backtest: BacktestReport
    watch_outcome: OutcomeSummary
    rejected_outcome: OutcomeSummary
    regime_performance: tuple[RegimePerformance, ...]
    score_sensitivity: tuple[ScoreThresholdSensitivity, ...]


@dataclass(frozen=True)
class StrategyValidationReport:
    strategy: str
    calibration: SegmentValidation
    validation: SegmentValidation
    out_of_sample: SegmentValidation
    expectancy_sign_consistent: bool | None
    oos_expectancy_vs_calibration_ratio: float | None
    oos_drawdown_degradation_pct_points: float | None


def _mean(values: list[float]) -> float | None:
    return fmean(values) if values else None


def regime_performance(report: BacktestReport) -> tuple[RegimePerformance, ...]:
    regimes = sorted({trade.market_regime or "unknown" for trade in report.trades})
    result: list[RegimePerformance] = []
    for regime in regimes:
        trades = [
            trade
            for trade in report.trades
            if (trade.market_regime or "unknown") == regime
        ]
        pnls = [trade.pnl_usd for trade in trades]
        wins = sum(value > 0 for value in pnls)
        result.append(
            RegimePerformance(
                regime=regime,
                trades=len(trades),
                net_pnl_usd=sum(pnls),
                expectancy_usd=_mean(pnls),
                win_rate_pct=(wins / len(trades) * 100.0) if trades else None,
            )
        )
    return tuple(result)


def score_threshold_sensitivity(
    observations: Sequence[OutcomeObservation],
    *,
    strategy: str,
    horizon: str = "24h",
    thresholds: Sequence[float] = (65.0, 70.0, 75.0, 80.0, 85.0),
) -> tuple[ScoreThresholdSensitivity, ...]:
    result: list[ScoreThresholdSensitivity] = []
    for threshold in thresholds:
        selected = [
            observation
            for observation in observations
            if observation.source == "strategy"
            and observation.strategy == strategy
            and observation.state is StrategyState.WATCH
            and observation.score >= threshold
            and observation.window_for(horizon) is not None
        ]
        directional = [
            observation.window_for(horizon).directional_return_pct
            for observation in selected
            if observation.window_for(horizon) is not None
            and observation.window_for(horizon).directional_return_pct is not None
        ]
        directional_values = [float(value) for value in directional]
        hit_rate = None
        if directional_values:
            hit_rate = (
                sum(value > 0 for value in directional_values)
                / len(directional_values)
                * 100.0
            )
        result.append(
            ScoreThresholdSensitivity(
                threshold=float(threshold),
                observations=len(selected),
                avg_directional_return_pct=_mean(directional_values),
                directional_hit_rate_pct=hit_rate,
            )
        )
    return tuple(result)


class TemporalValidator:
    """Chronological calibration/validation/out-of-sample validator.

    The split is deterministic and never shuffled. Future candles are truncated
    at each segment boundary before outcome/backtest evaluation.
    """

    def __init__(
        self,
        *,
        backtest_simulator: BacktestSimulator | None = None,
        outcome_evaluator: OutcomeEvaluator | None = None,
        split_config: TemporalSplitConfig | None = None,
        outcome_horizon: str = "24h",
    ):
        self.backtest_simulator = backtest_simulator or BacktestSimulator()
        self.outcome_evaluator = outcome_evaluator or OutcomeEvaluator()
        self.split_config = split_config or TemporalSplitConfig()
        self.outcome_horizon = outcome_horizon

    def split_points(
        self,
        points: Sequence[HistoricalPoint],
    ) -> dict[ValidationSegment, tuple[HistoricalPoint, ...]]:
        ordered = tuple(sorted(points, key=lambda point: point.timestamp_ms))
        minimum = self.split_config.min_points_per_segment * 3
        if len(ordered) < minimum:
            raise ValueError(
                f"at least {minimum} historical points are required for temporal validation"
            )

        total = len(ordered)
        calibration_end = int(total * self.split_config.calibration_ratio)
        validation_end = calibration_end + int(
            total * self.split_config.validation_ratio
        )

        calibration = ordered[:calibration_end]
        validation = ordered[calibration_end:validation_end]
        out_of_sample = ordered[validation_end:]

        segments = {
            ValidationSegment.CALIBRATION: calibration,
            ValidationSegment.VALIDATION: validation,
            ValidationSegment.OUT_OF_SAMPLE: out_of_sample,
        }
        for name, segment in segments.items():
            if len(segment) < self.split_config.min_points_per_segment:
                raise ValueError(
                    f"{name.value} has only {len(segment)} points; "
                    f"minimum is {self.split_config.min_points_per_segment}"
                )
        return segments

    @staticmethod
    def _candles_until(
        candles_by_interval: Mapping[str, Sequence[Candle]],
        *,
        end_timestamp_ms: int,
    ) -> dict[str, tuple[Candle, ...]]:
        return {
            interval: tuple(
                candle
                for candle in candles
                if candle.close_time_ms <= end_timestamp_ms
            )
            for interval, candles in candles_by_interval.items()
        }

    def _segment(
        self,
        *,
        segment: ValidationSegment,
        strategy: str,
        points: tuple[HistoricalPoint, ...],
        candles_by_interval: Mapping[str, Sequence[Candle]],
    ) -> SegmentValidation:
        start_ms = points[0].timestamp_ms
        end_ms = points[-1].timestamp_ms
        bounded_candles = self._candles_until(
            candles_by_interval,
            end_timestamp_ms=end_ms,
        )

        backtest = self.backtest_simulator.run_strategy(
            strategy=strategy,
            points=points,
            candles_by_interval=bounded_candles,
        )
        observations = self.outcome_evaluator.evaluate_points(
            points=points,
            candles_by_interval=bounded_candles,
        )
        watch = summarize_outcomes(
            observations,
            horizon=self.outcome_horizon,
            source="strategy",
            strategy=strategy,
            state=StrategyState.WATCH,
        )
        rejected = summarize_outcomes(
            observations,
            horizon=self.outcome_horizon,
            source="strategy",
            strategy=strategy,
            state=StrategyState.REJECT,
        )

        return SegmentValidation(
            segment=segment,
            start_timestamp_ms=start_ms,
            end_timestamp_ms=end_ms,
            backtest=backtest,
            watch_outcome=watch,
            rejected_outcome=rejected,
            regime_performance=regime_performance(backtest),
            score_sensitivity=score_threshold_sensitivity(
                observations,
                strategy=strategy,
                horizon=self.outcome_horizon,
            ),
        )

    @staticmethod
    def _expectancy_sign_consistency(
        segments: Sequence[SegmentValidation],
    ) -> bool | None:
        values = [
            segment.backtest.expectancy_usd
            for segment in segments
            if segment.backtest.expectancy_usd is not None
        ]
        if len(values) < 2:
            return None
        signs = {1 if value > 0 else -1 if value < 0 else 0 for value in values}
        return len(signs) == 1

    def validate_strategy(
        self,
        *,
        strategy: str,
        points: Sequence[HistoricalPoint],
        candles_by_interval: Mapping[str, Sequence[Candle]],
    ) -> StrategyValidationReport:
        split = self.split_points(points)
        calibration = self._segment(
            segment=ValidationSegment.CALIBRATION,
            strategy=strategy,
            points=split[ValidationSegment.CALIBRATION],
            candles_by_interval=candles_by_interval,
        )
        validation = self._segment(
            segment=ValidationSegment.VALIDATION,
            strategy=strategy,
            points=split[ValidationSegment.VALIDATION],
            candles_by_interval=candles_by_interval,
        )
        out_of_sample = self._segment(
            segment=ValidationSegment.OUT_OF_SAMPLE,
            strategy=strategy,
            points=split[ValidationSegment.OUT_OF_SAMPLE],
            candles_by_interval=candles_by_interval,
        )

        cal_expectancy = calibration.backtest.expectancy_usd
        oos_expectancy = out_of_sample.backtest.expectancy_usd
        expectancy_ratio = None
        if (
            cal_expectancy is not None
            and oos_expectancy is not None
            and cal_expectancy != 0
        ):
            expectancy_ratio = oos_expectancy / cal_expectancy

        drawdown_degradation = (
            out_of_sample.backtest.max_closed_equity_drawdown_pct
            - calibration.backtest.max_closed_equity_drawdown_pct
        )

        segments = (calibration, validation, out_of_sample)
        return StrategyValidationReport(
            strategy=strategy,
            calibration=calibration,
            validation=validation,
            out_of_sample=out_of_sample,
            expectancy_sign_consistent=self._expectancy_sign_consistency(segments),
            oos_expectancy_vs_calibration_ratio=expectancy_ratio,
            oos_drawdown_degradation_pct_points=drawdown_degradation,
        )

    def validate_all_strategies(
        self,
        *,
        points: Sequence[HistoricalPoint],
        candles_by_interval: Mapping[str, Sequence[Candle]],
    ) -> tuple[StrategyValidationReport, ...]:
        names = sorted(
            {
                assessment.strategy
                for point in points
                for assessment in point.assessments
            }
        )
        return tuple(
            self.validate_strategy(
                strategy=name,
                points=points,
                candles_by_interval=candles_by_interval,
            )
            for name in names
        )
