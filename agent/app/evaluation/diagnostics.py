from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import fmean
from typing import Mapping, Sequence

from app.evaluation.historical import HistoricalPoint
from app.evaluation.validation import (
    TemporalSplitConfig,
    TemporalValidator,
    ValidationSegment,
)
from app.market.binance_public import INTERVAL_MS
from app.market.types import Candle
from app.strategies.base import (
    HypothesisDirection,
    StrategyAssessment,
    StrategyState,
)


HOUR_MS = 60 * 60 * 1000
DEFAULT_DIAGNOSTIC_HORIZONS_HOURS = (1, 2, 4, 8, 12, 24, 48)
DEFAULT_FIXED_EXIT_HOURS = (4, 8, 12, 24, 48)
DEFAULT_ATR_STOP_MULTIPLIERS = (0.75, 1.0, 1.25, 1.5, 2.0)
DEFAULT_ATR_TARGET_MULTIPLIERS = (0.75, 1.0, 1.5, 2.0, 3.0)


@dataclass(frozen=True)
class DiagnosticConfig:
    fee_bps: float = 10.0
    slippage_bps: float = 5.0
    notional_usd: float = 100.0
    outcome_interval: str = "1h"
    current_max_holding_ms: int = 24 * HOUR_MS
    research_max_holding_ms: int = 48 * HOUR_MS
    require_entry_range: bool = True
    significant_mfe_pct: float = 0.5

    def __post_init__(self) -> None:
        if self.fee_bps < 0 or self.slippage_bps < 0:
            raise ValueError("fee/slippage cannot be negative")
        if self.notional_usd <= 0:
            raise ValueError("notional_usd must be positive")
        if self.current_max_holding_ms <= 0 or self.research_max_holding_ms <= 0:
            raise ValueError("holding horizons must be positive")
        if self.research_max_holding_ms < self.current_max_holding_ms:
            raise ValueError("research horizon must be >= current horizon")
        if self.significant_mfe_pct < 0:
            raise ValueError("significant_mfe_pct cannot be negative")


@dataclass(frozen=True)
class HorizonSnapshot:
    horizon_hours: int
    raw_return_pct: float
    net_return_pct: float
    mfe_pct: float
    mae_pct: float


@dataclass(frozen=True)
class SignalPathDiagnostic:
    symbol: str
    strategy: str
    segment: str
    signal_timestamp_ms: int
    entry_timestamp_ms: int
    entry_price: float
    market_regime: str | None
    score: float
    confidence: float
    atr_1h: float | None
    configured_stop: float | None
    configured_tp1: float | None
    current_exit_reason: str | None
    current_exit_timestamp_ms: int | None
    current_return_pct: float | None
    mfe_pct: float
    mae_pct: float
    time_to_mfe_ms: int | None
    time_to_mae_ms: int | None
    intrabar_ambiguous: bool
    favorable_then_loss: bool
    stop_before_later_recovery: bool
    horizons: tuple[HorizonSnapshot, ...]


@dataclass(frozen=True)
class Distribution:
    observations: int
    mean: float | None
    p25: float | None
    p50: float | None
    p75: float | None
    p90: float | None


@dataclass(frozen=True)
class TimingDistribution:
    observations: int
    median_ms: float | None
    p75_ms: float | None


@dataclass(frozen=True)
class HorizonSummary:
    horizon_hours: int
    observations: int
    average_return_pct: float | None
    median_return_pct: float | None
    positive_return_rate_pct: float | None
    average_raw_return_pct: float | None


@dataclass(frozen=True)
class GroupSummary:
    dimension: str
    key: str
    observations: int
    mfe: Distribution
    mae: Distribution
    time_to_mfe: TimingDistribution
    time_to_mae: TimingDistribution
    horizon_returns: tuple[HorizonSummary, ...]


@dataclass(frozen=True)
class ExitReasonSummary:
    reason: str
    trades: int
    share_pct: float
    expectancy_pct: float | None
    win_rate_pct: float | None
    avg_mfe_pct: float | None
    avg_mae_pct: float | None


@dataclass(frozen=True)
class CurrentExitAnalysis:
    trades: int
    reasons: tuple[ExitReasonSummary, ...]
    intrabar_ambiguous: int
    favorable_then_loss: int
    stop_before_later_recovery: int


@dataclass(frozen=True)
class ScenarioSummary:
    name: str
    segment: str
    observations: int
    net_pnl_usd: float
    expectancy_usd: float | None
    profit_factor: float | None
    win_rate_pct: float | None
    avg_return_pct: float | None


@dataclass(frozen=True)
class AtrScenarioSummary:
    segment: str
    stop_atr: float
    target_atr: float
    observations: int
    net_pnl_usd: float
    expectancy_usd: float | None
    profit_factor: float | None
    win_rate_pct: float | None
    research_eligible: bool


@dataclass(frozen=True)
class SegmentDiagnostics:
    segment: str
    paths: tuple[SignalPathDiagnostic, ...]
    group_summaries: tuple[GroupSummary, ...]
    current_exit: CurrentExitAnalysis
    fixed_horizon_scenarios: tuple[ScenarioSummary, ...]
    atr_sensitivity: tuple[AtrScenarioSummary, ...]


@dataclass(frozen=True)
class SymbolDiagnostics:
    symbol: str
    strategy: str
    segments: tuple[SegmentDiagnostics, ...]
    skipped_sell: int
    skipped_non_watch: int
    skipped_no_entry: int


@dataclass(frozen=True)
class IntervalQualityDiagnostic:
    interval: str
    candles: int
    duplicate_open_times: int
    gap_count: int


@dataclass(frozen=True)
class DiagnosticsReport:
    strategy: str
    symbols: tuple[str, ...]
    fee_bps: float
    slippage_bps: float
    data_quality: tuple[tuple[str, tuple[IntervalQualityDiagnostic, ...]], ...]
    results: tuple[SymbolDiagnostics, ...]
    methodological_warnings: tuple[str, ...]


@dataclass(frozen=True)
class _PreparedSignal:
    public: SignalPathDiagnostic
    assessment: StrategyAssessment
    point: HistoricalPoint
    entry_market_price: float
    entry_execution_price: float
    path: tuple[Candle, ...]


def _percentile(values: Sequence[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _distribution(values: Sequence[float]) -> Distribution:
    clean = [float(value) for value in values]
    return Distribution(
        observations=len(clean),
        mean=fmean(clean) if clean else None,
        p25=_percentile(clean, 0.25),
        p50=_percentile(clean, 0.50),
        p75=_percentile(clean, 0.75),
        p90=_percentile(clean, 0.90),
    )


def _timing(values: Sequence[int]) -> TimingDistribution:
    clean = [float(value) for value in values]
    return TimingDistribution(
        observations=len(clean),
        median_ms=_percentile(clean, 0.50),
        p75_ms=_percentile(clean, 0.75),
    )


def interval_quality(
    interval: str,
    candles: Sequence[Candle],
) -> IntervalQualityDiagnostic:
    opens = [candle.open_time_ms for candle in candles]
    step = INTERVAL_MS[interval]
    return IntervalQualityDiagnostic(
        interval=interval,
        candles=len(candles),
        duplicate_open_times=len(opens) - len(set(opens)),
        gap_count=sum(
            1
            for previous, current in zip(opens, opens[1:])
            if current - previous > step
        ),
    )


class StrategyDiagnostics:
    """Research-only path and exit diagnostics for Spot BUY hypotheses.

    It never creates orders and never treats SELL hypotheses as shorts.
    Segment candles are bounded before analysis to preserve temporal isolation.
    """

    def __init__(
        self,
        config: DiagnosticConfig | None = None,
        split_config: TemporalSplitConfig | None = None,
    ):
        self.config = config or DiagnosticConfig()
        self.split_config = split_config or TemporalSplitConfig(
            calibration_ratio=0.60,
            validation_ratio=0.20,
            out_of_sample_ratio=0.20,
            min_points_per_segment=20,
        )
        self._splitter = TemporalValidator(split_config=self.split_config)

    @staticmethod
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

    def _entry_candle(
        self,
        point: HistoricalPoint,
        assessment: StrategyAssessment,
        candles: Sequence[Candle],
    ) -> Candle | None:
        candle = next(
            (item for item in candles if item.open_time_ms > point.timestamp_ms),
            None,
        )
        if candle is None:
            return None
        if self.config.require_entry_range:
            if assessment.entry_low is None or assessment.entry_high is None:
                return None
            if not assessment.entry_low <= candle.open <= assessment.entry_high:
                return None
        return candle

    def _entry_execution_price(self, price: float) -> float:
        return price * (1.0 + self.config.slippage_bps / 10_000.0)

    def _exit_execution_price(self, price: float) -> float:
        return price * (1.0 - self.config.slippage_bps / 10_000.0)

    def _net_trade(
        self,
        entry_market_price: float,
        exit_market_price: float,
    ) -> tuple[float, float]:
        fee_rate = self.config.fee_bps / 10_000.0
        entry_price = self._entry_execution_price(entry_market_price)
        exit_price = self._exit_execution_price(exit_market_price)
        quantity = self.config.notional_usd / entry_price
        entry_fee = self.config.notional_usd * fee_rate
        exit_gross = quantity * exit_price
        exit_fee = exit_gross * fee_rate
        pnl = exit_gross - exit_fee - self.config.notional_usd - entry_fee
        capital = self.config.notional_usd + entry_fee
        return pnl, (pnl / capital * 100.0 if capital else 0.0)

    @staticmethod
    def _path_until(
        candles: Sequence[Candle],
        *,
        entry_timestamp_ms: int,
        horizon_ms: int,
    ) -> tuple[Candle, ...]:
        end_ms = entry_timestamp_ms + horizon_ms
        return tuple(
            candle
            for candle in candles
            if candle.open_time_ms >= entry_timestamp_ms
            and candle.close_time_ms <= end_ms
        )

    @staticmethod
    def _extremes(
        path: Sequence[Candle],
        entry_execution_price: float,
        entry_timestamp_ms: int,
    ) -> tuple[float, float, int | None, int | None]:
        if not path:
            return 0.0, 0.0, None, None
        max_candle = max(path, key=lambda candle: candle.high)
        min_candle = min(path, key=lambda candle: candle.low)
        mfe = max((max_candle.high / entry_execution_price - 1.0) * 100.0, 0.0)
        mae = max((1.0 - min_candle.low / entry_execution_price) * 100.0, 0.0)
        return (
            mfe,
            mae,
            max_candle.close_time_ms - entry_timestamp_ms,
            min_candle.close_time_ms - entry_timestamp_ms,
        )

    def _horizon_snapshot(
        self,
        *,
        entry_candle: Candle,
        path: Sequence[Candle],
        horizon_hours: int,
    ) -> HorizonSnapshot | None:
        horizon_ms = horizon_hours * HOUR_MS
        target = entry_candle.open_time_ms + horizon_ms
        covered = [
            candle
            for candle in path
            if candle.close_time_ms <= target
        ]
        if not covered or covered[-1].close_time_ms < target - 1:
            return None
        exit_market_price = covered[-1].close
        raw_return = (exit_market_price / entry_candle.open - 1.0) * 100.0
        _, net_return = self._net_trade(entry_candle.open, exit_market_price)
        mfe, mae, _, _ = self._extremes(
            covered,
            self._entry_execution_price(entry_candle.open),
            entry_candle.open_time_ms,
        )
        return HorizonSnapshot(
            horizon_hours=horizon_hours,
            raw_return_pct=raw_return,
            net_return_pct=net_return,
            mfe_pct=mfe,
            mae_pct=mae,
        )

    def _current_exit(
        self,
        *,
        assessment: StrategyAssessment,
        entry_candle: Candle,
        path: Sequence[Candle],
    ) -> tuple[str | None, int | None, float | None, bool]:
        stop = assessment.stop
        target = assessment.tp1
        exit_target_ms = entry_candle.open_time_ms + self.config.current_max_holding_ms
        for candle in path:
            stop_hit = stop is not None and candle.low <= stop
            target_hit = target is not None and candle.high >= target
            if stop_hit:
                _, net_return = self._net_trade(entry_candle.open, float(stop))
                return "STOP", candle.close_time_ms, net_return, bool(target_hit)
            if target_hit:
                _, net_return = self._net_trade(entry_candle.open, float(target))
                return "TP1", candle.close_time_ms, net_return, False
            if candle.close_time_ms >= exit_target_ms:
                _, net_return = self._net_trade(entry_candle.open, candle.close)
                return "HORIZON", candle.close_time_ms, net_return, False
        return None, None, None, False

    def _prepare(
        self,
        *,
        strategy: str,
        segment: ValidationSegment,
        point: HistoricalPoint,
        candles: Sequence[Candle],
    ) -> _PreparedSignal | None:
        assessment = self._assessment_for(point, strategy)
        if (
            assessment is None
            or assessment.state is not StrategyState.WATCH
            or assessment.direction is not HypothesisDirection.BUY
        ):
            return None
        entry = self._entry_candle(point, assessment, candles)
        if entry is None:
            return None
        path = self._path_until(
            candles,
            entry_timestamp_ms=entry.open_time_ms,
            horizon_ms=self.config.research_max_holding_ms,
        )
        if not path:
            return None

        entry_execution = self._entry_execution_price(entry.open)
        mfe, mae, time_to_mfe, time_to_mae = self._extremes(
            path,
            entry_execution,
            entry.open_time_ms,
        )
        exit_reason, exit_timestamp, current_return, ambiguous = self._current_exit(
            assessment=assessment,
            entry_candle=entry,
            path=path,
        )
        horizons = tuple(
            snapshot
            for hours in DEFAULT_DIAGNOSTIC_HORIZONS_HOURS
            if (
                snapshot := self._horizon_snapshot(
                    entry_candle=entry,
                    path=path,
                    horizon_hours=hours,
                )
            )
            is not None
        )
        favorable_then_loss = bool(
            current_return is not None
            and current_return < 0
            and mfe >= self.config.significant_mfe_pct
        )
        later_recovery = False
        if exit_reason == "STOP" and exit_timestamp is not None:
            later = [candle for candle in path if candle.close_time_ms > exit_timestamp]
            if later:
                later_mfe = max(
                    (candle.high / entry_execution - 1.0) * 100.0
                    for candle in later
                )
                later_recovery = later_mfe >= self.config.significant_mfe_pct

        h1 = point.candidate.analysis_for("1h")
        h4 = point.candidate.analysis_for("4h")
        public = SignalPathDiagnostic(
            symbol=assessment.symbol,
            strategy=strategy,
            segment=segment.value,
            signal_timestamp_ms=point.timestamp_ms,
            entry_timestamp_ms=entry.open_time_ms,
            entry_price=entry_execution,
            market_regime=(h4 or h1).regime.value if (h4 or h1) else None,
            score=assessment.score,
            confidence=assessment.confidence,
            atr_1h=h1.indicators.atr if h1 else None,
            configured_stop=assessment.stop,
            configured_tp1=assessment.tp1,
            current_exit_reason=exit_reason,
            current_exit_timestamp_ms=exit_timestamp,
            current_return_pct=current_return,
            mfe_pct=mfe,
            mae_pct=mae,
            time_to_mfe_ms=time_to_mfe,
            time_to_mae_ms=time_to_mae,
            intrabar_ambiguous=ambiguous,
            favorable_then_loss=favorable_then_loss,
            stop_before_later_recovery=later_recovery,
            horizons=horizons,
        )
        return _PreparedSignal(
            public=public,
            assessment=assessment,
            point=point,
            entry_market_price=entry.open,
            entry_execution_price=entry_execution,
            path=path,
        )

    @staticmethod
    def _horizon_summaries(
        paths: Sequence[SignalPathDiagnostic],
    ) -> tuple[HorizonSummary, ...]:
        result: list[HorizonSummary] = []
        for hours in DEFAULT_DIAGNOSTIC_HORIZONS_HOURS:
            snapshots = [
                snapshot
                for path in paths
                for snapshot in path.horizons
                if snapshot.horizon_hours == hours
            ]
            net = [snapshot.net_return_pct for snapshot in snapshots]
            raw = [snapshot.raw_return_pct for snapshot in snapshots]
            result.append(
                HorizonSummary(
                    horizon_hours=hours,
                    observations=len(net),
                    average_return_pct=fmean(net) if net else None,
                    median_return_pct=_percentile(net, 0.50),
                    positive_return_rate_pct=(
                        sum(value > 0 for value in net) / len(net) * 100.0
                        if net
                        else None
                    ),
                    average_raw_return_pct=fmean(raw) if raw else None,
                )
            )
        return tuple(result)

    @classmethod
    def _group_summary(
        cls,
        dimension: str,
        key: str,
        paths: Sequence[SignalPathDiagnostic],
    ) -> GroupSummary:
        return GroupSummary(
            dimension=dimension,
            key=key,
            observations=len(paths),
            mfe=_distribution([path.mfe_pct for path in paths]),
            mae=_distribution([path.mae_pct for path in paths]),
            time_to_mfe=_timing(
                [
                    path.time_to_mfe_ms
                    for path in paths
                    if path.time_to_mfe_ms is not None
                ]
            ),
            time_to_mae=_timing(
                [
                    path.time_to_mae_ms
                    for path in paths
                    if path.time_to_mae_ms is not None
                ]
            ),
            horizon_returns=cls._horizon_summaries(paths),
        )

    @classmethod
    def _groups(
        cls,
        paths: Sequence[SignalPathDiagnostic],
    ) -> tuple[GroupSummary, ...]:
        groups: list[GroupSummary] = [
            cls._group_summary("strategy", paths[0].strategy, paths)
        ] if paths else []
        for dimension, getter in (
            ("symbol", lambda item: item.symbol),
            ("regime", lambda item: item.market_regime or "unknown"),
            ("segment", lambda item: item.segment),
        ):
            for key in sorted({getter(path) for path in paths}):
                selected = [path for path in paths if getter(path) == key]
                groups.append(cls._group_summary(dimension, key, selected))
        return tuple(groups)

    @staticmethod
    def _current_exit_analysis(
        paths: Sequence[SignalPathDiagnostic],
    ) -> CurrentExitAnalysis:
        completed = [
            path
            for path in paths
            if path.current_exit_reason is not None
            and path.current_return_pct is not None
        ]
        reasons: list[ExitReasonSummary] = []
        for reason in ("STOP", "TP1", "HORIZON"):
            selected = [path for path in completed if path.current_exit_reason == reason]
            returns = [float(path.current_return_pct) for path in selected]
            reasons.append(
                ExitReasonSummary(
                    reason=reason,
                    trades=len(selected),
                    share_pct=(len(selected) / len(completed) * 100.0) if completed else 0.0,
                    expectancy_pct=fmean(returns) if returns else None,
                    win_rate_pct=(
                        sum(value > 0 for value in returns) / len(returns) * 100.0
                        if returns
                        else None
                    ),
                    avg_mfe_pct=(
                        fmean(path.mfe_pct for path in selected) if selected else None
                    ),
                    avg_mae_pct=(
                        fmean(path.mae_pct for path in selected) if selected else None
                    ),
                )
            )
        return CurrentExitAnalysis(
            trades=len(completed),
            reasons=tuple(reasons),
            intrabar_ambiguous=sum(path.intrabar_ambiguous for path in completed),
            favorable_then_loss=sum(path.favorable_then_loss for path in completed),
            stop_before_later_recovery=sum(
                path.stop_before_later_recovery for path in completed
            ),
        )

    def _scenario_metrics(
        self,
        returns: Sequence[float],
        *,
        name: str,
        segment: ValidationSegment,
    ) -> ScenarioSummary:
        pnls = [self.config.notional_usd * value / 100.0 for value in returns]
        wins = [value for value in pnls if value > 0]
        losses = [value for value in pnls if value < 0]
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        return ScenarioSummary(
            name=name,
            segment=segment.value,
            observations=len(pnls),
            net_pnl_usd=sum(pnls),
            expectancy_usd=(fmean(pnls) if pnls else None),
            profit_factor=(
                gross_profit / gross_loss
                if gross_loss > 0
                else None
            ),
            win_rate_pct=(
                len(wins) / len(pnls) * 100.0 if pnls else None
            ),
            avg_return_pct=fmean(returns) if returns else None,
        )

    def _fixed_horizon_scenarios(
        self,
        prepared: Sequence[_PreparedSignal],
        segment: ValidationSegment,
    ) -> tuple[ScenarioSummary, ...]:
        result: list[ScenarioSummary] = []
        current_returns = [
            float(item.public.current_return_pct)
            for item in prepared
            if item.public.current_return_pct is not None
        ]
        result.append(
            self._scenario_metrics(
                current_returns,
                name="current_strategy_exit",
                segment=segment,
            )
        )
        for hours in DEFAULT_FIXED_EXIT_HOURS:
            returns = [
                snapshot.net_return_pct
                for item in prepared
                for snapshot in item.public.horizons
                if snapshot.horizon_hours == hours
            ]
            result.append(
                self._scenario_metrics(
                    returns,
                    name=f"fixed_{hours}h",
                    segment=segment,
                )
            )
        return tuple(result)

    def _atr_return(
        self,
        item: _PreparedSignal,
        *,
        stop_atr: float,
        target_atr: float,
    ) -> float | None:
        atr = item.public.atr_1h
        if atr is None or atr <= 0:
            return None
        stop = item.entry_market_price - atr * stop_atr
        target = item.entry_market_price + atr * target_atr
        horizon_end = item.public.entry_timestamp_ms + self.config.current_max_holding_ms
        for candle in item.path:
            if candle.close_time_ms > horizon_end:
                break
            stop_hit = candle.low <= stop
            target_hit = candle.high >= target
            if stop_hit:
                return self._net_trade(item.entry_market_price, stop)[1]
            if target_hit:
                return self._net_trade(item.entry_market_price, target)[1]
            if candle.close_time_ms >= horizon_end:
                return self._net_trade(item.entry_market_price, candle.close)[1]
        return None

    def _atr_sensitivity(
        self,
        prepared: Sequence[_PreparedSignal],
        segment: ValidationSegment,
    ) -> tuple[AtrScenarioSummary, ...]:
        result: list[AtrScenarioSummary] = []
        for stop_atr in DEFAULT_ATR_STOP_MULTIPLIERS:
            for target_atr in DEFAULT_ATR_TARGET_MULTIPLIERS:
                returns = [
                    value
                    for item in prepared
                    if (
                        value := self._atr_return(
                            item,
                            stop_atr=stop_atr,
                            target_atr=target_atr,
                        )
                    )
                    is not None
                ]
                pnls = [self.config.notional_usd * value / 100.0 for value in returns]
                wins = [value for value in pnls if value > 0]
                losses = [value for value in pnls if value < 0]
                gross_profit = sum(wins)
                gross_loss = abs(sum(losses))
                result.append(
                    AtrScenarioSummary(
                        segment=segment.value,
                        stop_atr=stop_atr,
                        target_atr=target_atr,
                        observations=len(pnls),
                        net_pnl_usd=sum(pnls),
                        expectancy_usd=fmean(pnls) if pnls else None,
                        profit_factor=(
                            gross_profit / gross_loss
                            if gross_loss > 0
                            else None
                        ),
                        win_rate_pct=(
                            len(wins) / len(pnls) * 100.0 if pnls else None
                        ),
                        research_eligible=segment is not ValidationSegment.OUT_OF_SAMPLE,
                    )
                )
        return tuple(result)

    def run_symbol(
        self,
        *,
        strategy: str,
        points: Sequence[HistoricalPoint],
        candles_by_interval: Mapping[str, Sequence[Candle]],
    ) -> SymbolDiagnostics:
        candles = candles_by_interval.get(self.config.outcome_interval)
        if not candles:
            raise ValueError(
                f"missing outcome interval {self.config.outcome_interval}"
            )
        split = self._splitter.split_points(points)
        skipped_sell = 0
        skipped_non_watch = 0
        skipped_no_entry = 0
        segments: list[SegmentDiagnostics] = []

        for segment in (
            ValidationSegment.CALIBRATION,
            ValidationSegment.VALIDATION,
            ValidationSegment.OUT_OF_SAMPLE,
        ):
            segment_points = split[segment]
            segment_end = segment_points[-1].timestamp_ms
            bounded = tuple(
                candle for candle in candles if candle.close_time_ms <= segment_end
            )
            prepared: list[_PreparedSignal] = []
            for point in segment_points:
                assessment = self._assessment_for(point, strategy)
                if assessment is None or assessment.state is not StrategyState.WATCH:
                    skipped_non_watch += 1
                    continue
                if assessment.direction is HypothesisDirection.SELL:
                    skipped_sell += 1
                    continue
                if assessment.direction is not HypothesisDirection.BUY:
                    skipped_non_watch += 1
                    continue
                if self._entry_candle(point, assessment, bounded) is None:
                    skipped_no_entry += 1
                    continue
                item = self._prepare(
                    strategy=strategy,
                    segment=segment,
                    point=point,
                    candles=bounded,
                )
                if item is not None:
                    prepared.append(item)

            public_paths = tuple(item.public for item in prepared)
            segments.append(
                SegmentDiagnostics(
                    segment=segment.value,
                    paths=public_paths,
                    group_summaries=self._groups(public_paths),
                    current_exit=self._current_exit_analysis(public_paths),
                    fixed_horizon_scenarios=self._fixed_horizon_scenarios(
                        prepared,
                        segment,
                    ),
                    atr_sensitivity=self._atr_sensitivity(prepared, segment),
                )
            )

        symbol = points[0].candidate.symbol if points else ""
        return SymbolDiagnostics(
            symbol=symbol,
            strategy=strategy,
            segments=tuple(segments),
            skipped_sell=skipped_sell,
            skipped_non_watch=skipped_non_watch,
            skipped_no_entry=skipped_no_entry,
        )


def diagnostics_to_dict(report: DiagnosticsReport) -> dict:
    return asdict(report)
