from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean
from typing import Mapping, Sequence

from app.evaluation.diagnostics import (
    DiagnosticConfig,
    StrategyDiagnostics,
)
from app.evaluation.historical import HistoricalPoint
from app.evaluation.validation import TemporalSplitConfig, ValidationSegment
from app.market.types import Candle, TimeframeAnalysis
from app.strategies.base import HypothesisDirection, StrategyAssessment, StrategyState


HOUR_MS = 60 * 60 * 1000
DEFAULT_OUTCOME_HOURS = 24
DEFAULT_CLUSTER_HOURS = 6
DEFAULT_MIN_BUCKET_OBSERVATIONS = 20


@dataclass(frozen=True)
class EntryFeatureSnapshot:
    symbol: str
    segment: str
    signal_timestamp_ms: int
    score: float
    confidence: float
    rsi_1h: float
    atr_pct_1h: float
    volume_ratio_1h: float
    ema_distance_pct_1h: float
    ema_spread_pct_1h: float
    rsi_15m: float | None
    ema_distance_pct_15m: float | None
    rsi_4h: float | None
    ema_distance_pct_4h: float | None
    below_ema_fast_timeframes: int
    structure_1h: str
    structure_4h: str | None
    hours_since_previous_watch_buy: float | None
    watch_buy_signals_last_6h: int
    outcome_hours: int
    net_return_pct: float
    positive_return: bool


@dataclass(frozen=True)
class EntryBucketSummary:
    segment: str
    feature: str
    bucket: str
    observations: int
    average_return_pct: float
    median_return_pct: float
    positive_return_rate_pct: float
    baseline_return_pct: float
    uplift_vs_baseline_pct_points: float
    sufficient_sample: bool
    research_eligible: bool


@dataclass(frozen=True)
class CrossSegmentBucketEvidence:
    feature: str
    bucket: str
    calibration_observations: int
    validation_observations: int
    calibration_average_return_pct: float | None
    validation_average_return_pct: float | None
    calibration_uplift_pct_points: float | None
    validation_uplift_pct_points: float | None
    stable_positive_uplift: bool
    stable_positive_return: bool
    sufficient_sample_both: bool


@dataclass(frozen=True)
class EntrySegmentReport:
    segment: str
    observations: tuple[EntryFeatureSnapshot, ...]
    baseline_return_pct: float | None
    buckets: tuple[EntryBucketSummary, ...]
    research_eligible: bool


@dataclass(frozen=True)
class EntryQualitySymbolReport:
    symbol: str
    strategy: str
    outcome_hours: int
    segments: tuple[EntrySegmentReport, ...]
    cross_segment_evidence: tuple[CrossSegmentBucketEvidence, ...]


@dataclass(frozen=True)
class EntryQualityPooledReport:
    strategy: str
    symbols: tuple[str, ...]
    outcome_hours: int
    segments: tuple[EntrySegmentReport, ...]
    cross_segment_evidence: tuple[CrossSegmentBucketEvidence, ...]


def _percentile(values: Sequence[float], percentile: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("cannot calculate percentile of empty values")
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _median(values: Sequence[float]) -> float:
    return _percentile(values, 0.5)


def _assessment_for(
    point: HistoricalPoint,
    strategy: str,
) -> StrategyAssessment | None:
    return next(
        (
            assessment
            for assessment in point.assessments
            if assessment.strategy == strategy
        ),
        None,
    )


def _ema_distance_pct(analysis: TimeframeAnalysis) -> float:
    ema = analysis.indicators.ema_fast
    if ema == 0:
        return 0.0
    return (analysis.last_price / ema - 1.0) * 100.0


def _ema_spread_pct(analysis: TimeframeAnalysis) -> float:
    slow = analysis.indicators.ema_slow
    if slow == 0:
        return 0.0
    return (analysis.indicators.ema_fast / slow - 1.0) * 100.0


def _numeric_bucket(feature: str, value: float | int | None) -> str:
    if value is None:
        return "missing"
    number = float(value)
    if feature == "score":
        return "72-77.99" if number < 78 else "78-84.99" if number < 85 else "85+"
    if feature == "confidence":
        return "<76" if number < 76 else "76-78.99" if number < 79 else "79+"
    if feature == "rsi_1h":
        return "<=25" if number <= 25 else "25-30" if number <= 30 else "30-35"
    if feature == "atr_pct_1h":
        return "<1.5" if number < 1.5 else "1.5-3" if number < 3 else "3-4.5" if number < 4.5 else "4.5+"
    if feature == "volume_ratio_1h":
        return "<=0.75" if number <= 0.75 else "0.75-1.5" if number <= 1.5 else "1.5-2.5" if number <= 2.5 else "2.5+"
    if feature in {"ema_distance_pct_1h", "ema_distance_pct_15m"}:
        return "<=-3" if number <= -3 else "-3--1.5" if number <= -1.5 else "-1.5-0" if number < 0 else ">=0"
    if feature == "ema_spread_pct_1h":
        return "<=-2" if number <= -2 else "-2--0.5" if number <= -0.5 else "-0.5-0.5" if number < 0.5 else ">=0.5"
    if feature == "rsi_15m":
        return "<30" if number < 30 else "30-45" if number < 45 else "45-55" if number < 55 else "55+"
    if feature == "rsi_4h":
        return "<40" if number < 40 else "40-50" if number < 50 else "50-60" if number < 60 else "60+"
    if feature == "ema_distance_pct_4h":
        return "<=-2" if number <= -2 else "-2-0" if number < 0 else "0-2" if number < 2 else ">=2"
    if feature == "below_ema_fast_timeframes":
        return str(int(number))
    if feature == "hours_since_previous_watch_buy":
        return "first" if value is None else "<2h" if number < 2 else "2-6h" if number < 6 else "6-24h" if number < 24 else "24h+"
    if feature == "watch_buy_signals_last_6h":
        return "1" if number <= 1 else "2" if number == 2 else "3-4" if number <= 4 else "5+"
    raise KeyError(feature)


_NUMERIC_FEATURES = (
    "score",
    "confidence",
    "rsi_1h",
    "atr_pct_1h",
    "volume_ratio_1h",
    "ema_distance_pct_1h",
    "ema_spread_pct_1h",
    "rsi_15m",
    "ema_distance_pct_15m",
    "rsi_4h",
    "ema_distance_pct_4h",
    "below_ema_fast_timeframes",
    "hours_since_previous_watch_buy",
    "watch_buy_signals_last_6h",
)

_CATEGORICAL_FEATURES = (
    "symbol",
    "structure_1h",
    "structure_4h",
)


class MeanReversionEntryDiagnostics:
    """Research-only entry-quality diagnostics.

    Features are derived exclusively from information available at signal time.
    Future candles are used only as labels for the selected outcome horizon.
    """

    def __init__(
        self,
        *,
        outcome_hours: int = DEFAULT_OUTCOME_HOURS,
        cluster_hours: int = DEFAULT_CLUSTER_HOURS,
        min_bucket_observations: int = DEFAULT_MIN_BUCKET_OBSERVATIONS,
        diagnostics: StrategyDiagnostics | None = None,
        split_config: TemporalSplitConfig | None = None,
    ):
        if outcome_hours <= 0:
            raise ValueError("outcome_hours must be positive")
        if cluster_hours <= 0:
            raise ValueError("cluster_hours must be positive")
        if min_bucket_observations <= 0:
            raise ValueError("min_bucket_observations must be positive")
        self.outcome_hours = outcome_hours
        self.cluster_hours = cluster_hours
        self.min_bucket_observations = min_bucket_observations
        self.split_config = split_config or TemporalSplitConfig(
            calibration_ratio=0.60,
            validation_ratio=0.20,
            out_of_sample_ratio=0.20,
            min_points_per_segment=20,
        )
        self.diagnostics = diagnostics or StrategyDiagnostics(
            DiagnosticConfig(
                fee_bps=10,
                slippage_bps=5,
                notional_usd=100,
                require_entry_range=True,
            ),
            split_config=self.split_config,
        )

    @staticmethod
    def _is_watch_buy(point: HistoricalPoint, strategy: str) -> bool:
        assessment = _assessment_for(point, strategy)
        return bool(
            assessment is not None
            and assessment.state is StrategyState.WATCH
            and assessment.direction is HypothesisDirection.BUY
        )

    def _prior_signal_context(
        self,
        *,
        point: HistoricalPoint,
        watch_buy_timestamps: Sequence[int],
    ) -> tuple[float | None, int]:
        previous = [stamp for stamp in watch_buy_timestamps if stamp < point.timestamp_ms]
        since = None
        if previous:
            since = (point.timestamp_ms - previous[-1]) / HOUR_MS
        start = point.timestamp_ms - self.cluster_hours * HOUR_MS
        recent = sum(start < stamp <= point.timestamp_ms for stamp in watch_buy_timestamps)
        return since, recent

    def _features(
        self,
        *,
        point: HistoricalPoint,
        segment: ValidationSegment,
        strategy: str,
        net_return_pct: float,
        watch_buy_timestamps: Sequence[int],
    ) -> EntryFeatureSnapshot:
        assessment = _assessment_for(point, strategy)
        if assessment is None:
            raise ValueError("strategy assessment missing")
        h15 = point.candidate.analysis_for("15m")
        h1 = point.candidate.analysis_for("1h")
        h4 = point.candidate.analysis_for("4h")
        if h1 is None:
            raise ValueError("1h analysis required")

        analyses = [
            analysis
            for analysis in (
                point.candidate.analysis_for("15m"),
                h1,
                h4,
                point.candidate.analysis_for("1d"),
            )
            if analysis is not None
        ]
        below_count = sum(
            analysis.last_price < analysis.indicators.ema_fast
            for analysis in analyses
        )
        hours_since, recent = self._prior_signal_context(
            point=point,
            watch_buy_timestamps=watch_buy_timestamps,
        )
        return EntryFeatureSnapshot(
            symbol=point.candidate.symbol,
            segment=segment.value,
            signal_timestamp_ms=point.timestamp_ms,
            score=assessment.score,
            confidence=assessment.confidence,
            rsi_1h=h1.indicators.rsi,
            atr_pct_1h=h1.indicators.atr_pct,
            volume_ratio_1h=h1.indicators.volume_ratio,
            ema_distance_pct_1h=_ema_distance_pct(h1),
            ema_spread_pct_1h=_ema_spread_pct(h1),
            rsi_15m=h15.indicators.rsi if h15 else None,
            ema_distance_pct_15m=_ema_distance_pct(h15) if h15 else None,
            rsi_4h=h4.indicators.rsi if h4 else None,
            ema_distance_pct_4h=_ema_distance_pct(h4) if h4 else None,
            below_ema_fast_timeframes=below_count,
            structure_1h=h1.indicators.structure,
            structure_4h=h4.indicators.structure if h4 else None,
            hours_since_previous_watch_buy=hours_since,
            watch_buy_signals_last_6h=recent,
            outcome_hours=self.outcome_hours,
            net_return_pct=net_return_pct,
            positive_return=net_return_pct > 0,
        )

    def _bucket_summaries(
        self,
        *,
        segment: ValidationSegment,
        observations: Sequence[EntryFeatureSnapshot],
    ) -> tuple[EntryBucketSummary, ...]:
        if not observations:
            return ()
        baseline = fmean(item.net_return_pct for item in observations)
        summaries: list[EntryBucketSummary] = []
        for feature in _NUMERIC_FEATURES + _CATEGORICAL_FEATURES:
            grouped: dict[str, list[EntryFeatureSnapshot]] = {}
            for item in observations:
                value = getattr(item, feature)
                if feature in _NUMERIC_FEATURES:
                    bucket = _numeric_bucket(feature, value)
                else:
                    bucket = str(value) if value is not None else "missing"
                grouped.setdefault(bucket, []).append(item)
            for bucket in sorted(grouped):
                selected = grouped[bucket]
                returns = [item.net_return_pct for item in selected]
                average = fmean(returns)
                summaries.append(
                    EntryBucketSummary(
                        segment=segment.value,
                        feature=feature,
                        bucket=bucket,
                        observations=len(selected),
                        average_return_pct=average,
                        median_return_pct=_median(returns),
                        positive_return_rate_pct=(
                            sum(item.positive_return for item in selected)
                            / len(selected)
                            * 100.0
                        ),
                        baseline_return_pct=baseline,
                        uplift_vs_baseline_pct_points=average - baseline,
                        sufficient_sample=len(selected) >= self.min_bucket_observations,
                        research_eligible=segment is not ValidationSegment.OUT_OF_SAMPLE,
                    )
                )
        return tuple(summaries)

    def _segment_report(
        self,
        *,
        segment: ValidationSegment,
        observations: Sequence[EntryFeatureSnapshot],
    ) -> EntrySegmentReport:
        values = tuple(observations)
        return EntrySegmentReport(
            segment=segment.value,
            observations=values,
            baseline_return_pct=(
                fmean(item.net_return_pct for item in values) if values else None
            ),
            buckets=self._bucket_summaries(segment=segment, observations=values),
            research_eligible=segment is not ValidationSegment.OUT_OF_SAMPLE,
        )

    def _cross_segment(
        self,
        segments: Sequence[EntrySegmentReport],
    ) -> tuple[CrossSegmentBucketEvidence, ...]:
        by_segment = {segment.segment: segment for segment in segments}
        calibration = by_segment.get(ValidationSegment.CALIBRATION.value)
        validation = by_segment.get(ValidationSegment.VALIDATION.value)
        if calibration is None or validation is None:
            return ()

        cal = {(row.feature, row.bucket): row for row in calibration.buckets}
        val = {(row.feature, row.bucket): row for row in validation.buckets}
        result: list[CrossSegmentBucketEvidence] = []
        for key in sorted(set(cal) & set(val)):
            cal_row = cal[key]
            val_row = val[key]
            sufficient = cal_row.sufficient_sample and val_row.sufficient_sample
            result.append(
                CrossSegmentBucketEvidence(
                    feature=key[0],
                    bucket=key[1],
                    calibration_observations=cal_row.observations,
                    validation_observations=val_row.observations,
                    calibration_average_return_pct=cal_row.average_return_pct,
                    validation_average_return_pct=val_row.average_return_pct,
                    calibration_uplift_pct_points=cal_row.uplift_vs_baseline_pct_points,
                    validation_uplift_pct_points=val_row.uplift_vs_baseline_pct_points,
                    stable_positive_uplift=bool(
                        sufficient
                        and cal_row.uplift_vs_baseline_pct_points > 0
                        and val_row.uplift_vs_baseline_pct_points > 0
                    ),
                    stable_positive_return=bool(
                        sufficient
                        and cal_row.average_return_pct > 0
                        and val_row.average_return_pct > 0
                    ),
                    sufficient_sample_both=sufficient,
                )
            )
        return tuple(result)

    def run_symbol(
        self,
        *,
        strategy: str,
        points: Sequence[HistoricalPoint],
        candles_by_interval: Mapping[str, Sequence[Candle]],
    ) -> EntryQualitySymbolReport:
        diagnostics = self.diagnostics.run_symbol(
            strategy=strategy,
            points=points,
            candles_by_interval=candles_by_interval,
        )
        point_by_timestamp = {point.timestamp_ms: point for point in points}
        watch_buy_timestamps = tuple(
            point.timestamp_ms
            for point in sorted(points, key=lambda item: item.timestamp_ms)
            if self._is_watch_buy(point, strategy)
        )

        segment_reports: list[EntrySegmentReport] = []
        for segment_diag in diagnostics.segments:
            segment = ValidationSegment(segment_diag.segment)
            observations: list[EntryFeatureSnapshot] = []
            for path in segment_diag.paths:
                snapshot = next(
                    (
                        horizon
                        for horizon in path.horizons
                        if horizon.horizon_hours == self.outcome_hours
                    ),
                    None,
                )
                point = point_by_timestamp.get(path.signal_timestamp_ms)
                if snapshot is None or point is None:
                    continue
                observations.append(
                    self._features(
                        point=point,
                        segment=segment,
                        strategy=strategy,
                        net_return_pct=snapshot.net_return_pct,
                        watch_buy_timestamps=watch_buy_timestamps,
                    )
                )
            segment_reports.append(
                self._segment_report(segment=segment, observations=observations)
            )

        segments = tuple(segment_reports)
        return EntryQualitySymbolReport(
            symbol=diagnostics.symbol,
            strategy=strategy,
            outcome_hours=self.outcome_hours,
            segments=segments,
            cross_segment_evidence=self._cross_segment(segments),
        )

    def pool(
        self,
        reports: Sequence[EntryQualitySymbolReport],
        *,
        strategy: str,
    ) -> EntryQualityPooledReport:
        symbols = tuple(report.symbol for report in reports)
        pooled_segments: list[EntrySegmentReport] = []
        for segment in (
            ValidationSegment.CALIBRATION,
            ValidationSegment.VALIDATION,
            ValidationSegment.OUT_OF_SAMPLE,
        ):
            observations = [
                observation
                for report in reports
                for item in report.segments
                if item.segment == segment.value
                for observation in item.observations
            ]
            pooled_segments.append(
                self._segment_report(segment=segment, observations=observations)
            )
        segments = tuple(pooled_segments)
        return EntryQualityPooledReport(
            strategy=strategy,
            symbols=symbols,
            outcome_hours=self.outcome_hours,
            segments=segments,
            cross_segment_evidence=self._cross_segment(segments),
        )
