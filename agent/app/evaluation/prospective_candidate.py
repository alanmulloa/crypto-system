from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import fmean
from typing import Mapping, Sequence

from app.evaluation.candidate_experiment import CandidateDefinition, DEFAULT_CANDIDATES
from app.evaluation.historical import HistoricalPoint
from app.market.types import Candle
from app.strategies.base import HypothesisDirection, StrategyState


HOUR_MS = 60 * 60 * 1000
DEFAULT_OUTCOME_HOURS = 24
DEFAULT_MIN_MATURED_OBSERVATIONS = 20
DEFAULT_FREEZE_AT_ISO = "2026-11-10T22:10:15.195720+00:00"


@dataclass(frozen=True)
class ProspectiveObservation:
    cohort: str
    symbol: str
    signal_timestamp_ms: int
    entry_timestamp_ms: int | None
    entry_market_price: float | None
    feature_value: float | str | None
    status: str
    outcome_timestamp_ms: int | None
    gross_return_pct: float | None
    net_return_pct: float | None
    positive_return: bool | None


@dataclass(frozen=True)
class ProspectiveCohortSummary:
    cohort: str
    observations: int
    matured: int
    pending: int
    average_net_return_pct: float | None
    median_net_return_pct: float | None
    positive_return_rate_pct: float | None


@dataclass(frozen=True)
class ProspectiveCandidateReport:
    candidate: CandidateDefinition
    frozen_at_ms: int
    as_of_ms: int
    outcome_hours: int
    min_matured_observations: int
    baseline: ProspectiveCohortSummary
    candidate_summary: ProspectiveCohortSummary
    uplift_vs_baseline_pct_points: float | None
    sample_ready: bool
    observations: tuple[ProspectiveObservation, ...]
    methodological_warnings: tuple[str, ...]


def parse_iso_ms(value: str) -> int:
    return int(datetime.fromisoformat(value).timestamp() * 1000)


def _median(values: Sequence[float]) -> float | None:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


class ProspectiveXrpCandidateEvaluator:
    """Evaluate the frozen XRP candidate only on post-freeze observations.

    This module never executes orders. Lookback candles may predate the freeze only
    to construct signal-time indicators; observations must have timestamps strictly
    after the frozen cutoff.
    """

    def __init__(
        self,
        *,
        candidate: CandidateDefinition | None = None,
        frozen_at_ms: int | None = None,
        outcome_hours: int = DEFAULT_OUTCOME_HOURS,
        min_matured_observations: int = DEFAULT_MIN_MATURED_OBSERVATIONS,
        fee_bps: float = 10.0,
        slippage_bps: float = 5.0,
    ):
        selected = candidate or DEFAULT_CANDIDATES[0]
        if selected.name != "xrp_low_volume_1h":
            raise ValueError("prospective harness is frozen to xrp_low_volume_1h")
        if outcome_hours <= 0:
            raise ValueError("outcome_hours must be positive")
        if min_matured_observations <= 0:
            raise ValueError("min_matured_observations must be positive")
        if fee_bps < 0 or slippage_bps < 0:
            raise ValueError("fees/slippage cannot be negative")
        self.candidate = selected
        self.frozen_at_ms = (\n            parse_iso_ms(DEFAULT_FREEZE_AT_ISO)\n            if frozen_at_ms is None\n            else frozen_at_ms\n        )
        self.outcome_hours = outcome_hours
        self.min_matured_observations = min_matured_observations
        self.fee_bps = fee_bps
        self.slippage_bps = slippage_bps

    @staticmethod
    def _assessment(point: HistoricalPoint):
        return next(
            (
                assessment
                for assessment in point.assessments
                if assessment.strategy == "mean_reversion"
            ),
            None,
        )

    @staticmethod
    def _feature(point: HistoricalPoint) -> float | None:
        h1 = point.candidate.analysis_for("1h")
        return h1.indicators.volume_ratio if h1 is not None else None

    def _candidate_matches(self, point: HistoricalPoint) -> bool:
        if point.candidate.symbol != self.candidate.symbol:
            return False
        value = self._feature(point)
        return value is not None and value <= float(self.candidate.value)

    @staticmethod
    def _entry_candle(
        point: HistoricalPoint,
        candles: Sequence[Candle],
    ) -> Candle | None:
        assessment = ProspectiveXrpCandidateEvaluator._assessment(point)
        if assessment is None:
            return None
        candle = next(
            (item for item in candles if item.open_time_ms > point.timestamp_ms),
            None,
        )
        if candle is None:
            return None
        if assessment.entry_low is None or assessment.entry_high is None:
            return None
        if not assessment.entry_low <= candle.open <= assessment.entry_high:
            return None
        return candle

    def _net_return(self, entry_market_price: float, exit_market_price: float) -> float:
        fee_rate = self.fee_bps / 10_000.0
        entry = entry_market_price * (1.0 + self.slippage_bps / 10_000.0)
        exit_price = exit_market_price * (1.0 - self.slippage_bps / 10_000.0)
        notional = 100.0
        quantity = notional / entry
        entry_fee = notional * fee_rate
        exit_gross = quantity * exit_price
        exit_fee = exit_gross * fee_rate
        pnl = exit_gross - exit_fee - notional - entry_fee
        return pnl / (notional + entry_fee) * 100.0

    def _observe(
        self,
        *,
        point: HistoricalPoint,
        candles: Sequence[Candle],
        as_of_ms: int,
        cohort: str,
    ) -> ProspectiveObservation:
        entry = self._entry_candle(point, candles)
        feature = self._feature(point)
        if entry is None:
            return ProspectiveObservation(
                cohort=cohort,
                symbol=point.candidate.symbol,
                signal_timestamp_ms=point.timestamp_ms,
                entry_timestamp_ms=None,
                entry_market_price=None,
                feature_value=feature,
                status="NO_ENTRY",
                outcome_timestamp_ms=None,
                gross_return_pct=None,
                net_return_pct=None,
                positive_return=None,
            )

        target_ms = entry.open_time_ms + self.outcome_hours * HOUR_MS
        outcome = next(
            (
                candle
                for candle in candles
                if candle.close_time_ms >= target_ms - 1
                and candle.open_time_ms >= entry.open_time_ms
            ),
            None,
        )
        if outcome is None or outcome.close_time_ms > as_of_ms:
            return ProspectiveObservation(
                cohort=cohort,
                symbol=point.candidate.symbol,
                signal_timestamp_ms=point.timestamp_ms,
                entry_timestamp_ms=entry.open_time_ms,
                entry_market_price=entry.open,
                feature_value=feature,
                status="PENDING",
                outcome_timestamp_ms=target_ms,
                gross_return_pct=None,
                net_return_pct=None,
                positive_return=None,
            )

        gross = (outcome.close / entry.open - 1.0) * 100.0
        net = self._net_return(entry.open, outcome.close)
        return ProspectiveObservation(
            cohort=cohort,
            symbol=point.candidate.symbol,
            signal_timestamp_ms=point.timestamp_ms,
            entry_timestamp_ms=entry.open_time_ms,
            entry_market_price=entry.open,
            feature_value=feature,
            status="MATURED",
            outcome_timestamp_ms=outcome.close_time_ms,
            gross_return_pct=gross,
            net_return_pct=net,
            positive_return=net > 0,
        )

    @staticmethod
    def _summary(
        cohort: str,
        observations: Sequence[ProspectiveObservation],
    ) -> ProspectiveCohortSummary:
        matured = [
            observation
            for observation in observations
            if observation.status == "MATURED"
            and observation.net_return_pct is not None
        ]
        pending = [
            observation
            for observation in observations
            if observation.status == "PENDING"
        ]
        returns = [float(item.net_return_pct) for item in matured]
        return ProspectiveCohortSummary(
            cohort=cohort,
            observations=len(observations),
            matured=len(matured),
            pending=len(pending),
            average_net_return_pct=fmean(returns) if returns else None,
            median_net_return_pct=_median(returns),
            positive_return_rate_pct=(
                sum(value > 0 for value in returns) / len(returns) * 100.0
                if returns
                else None
            ),
        )

    def run(
        self,
        *,
        points: Sequence[HistoricalPoint],
        candles_by_interval: Mapping[str, Sequence[Candle]],
        as_of_ms: int,
    ) -> ProspectiveCandidateReport:
        candles = candles_by_interval.get("1h")
        if not candles:
            raise ValueError("1h candles required")
        if as_of_ms <= self.frozen_at_ms:
            raise ValueError("as_of_ms must be after frozen_at_ms")

        baseline_observations: list[ProspectiveObservation] = []
        candidate_observations: list[ProspectiveObservation] = []

        for point in sorted(points, key=lambda item: item.timestamp_ms):
            if point.timestamp_ms <= self.frozen_at_ms:
                continue
            if point.timestamp_ms > as_of_ms:
                continue
            if point.candidate.symbol != self.candidate.symbol:
                continue
            assessment = self._assessment(point)
            if (
                assessment is None
                or assessment.state is not StrategyState.WATCH
                or assessment.direction is not HypothesisDirection.BUY
            ):
                continue

            baseline_observations.append(
                self._observe(
                    point=point,
                    candles=candles,
                    as_of_ms=as_of_ms,
                    cohort="baseline",
                )
            )
            if self._candidate_matches(point):
                candidate_observations.append(
                    self._observe(
                        point=point,
                        candles=candles,
                        as_of_ms=as_of_ms,
                        cohort="candidate",
                    )
                )

        baseline = self._summary("baseline", baseline_observations)
        candidate_summary = self._summary("candidate", candidate_observations)
        uplift = None
        if (
            baseline.average_net_return_pct is not None
            and candidate_summary.average_net_return_pct is not None
        ):
            uplift = (
                candidate_summary.average_net_return_pct
                - baseline.average_net_return_pct
            )

        return ProspectiveCandidateReport(
            candidate=self.candidate,
            frozen_at_ms=self.frozen_at_ms,
            as_of_ms=as_of_ms,
            outcome_hours=self.outcome_hours,
            min_matured_observations=self.min_matured_observations,
            baseline=baseline,
            candidate_summary=candidate_summary,
            uplift_vs_baseline_pct_points=uplift,
            sample_ready=(
                candidate_summary.matured >= self.min_matured_observations
            ),
            observations=tuple(baseline_observations + candidate_observations),
            methodological_warnings=(
                "Only signal timestamps strictly after the frozen cutoff are included.",
                "Pre-freeze candles may be used only as indicator lookback.",
                "The candidate is frozen to XRPUSDT volume_ratio_1h <= 0.75.",
                "sample_ready is not an approval or automatic promotion rule.",
                "This module cannot place orders and does not use private Binance APIs.",
            ),
        )
