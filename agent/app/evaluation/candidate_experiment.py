from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean
from typing import Sequence

from app.evaluation.entry_quality import (
    EntryFeatureSnapshot,
    EntryQualitySymbolReport,
)
from app.evaluation.validation import ValidationSegment


@dataclass(frozen=True)
class CandidateDefinition:
    name: str
    symbol: str
    feature: str
    operator: str
    value: float | str
    description: str


@dataclass(frozen=True)
class CandidateSegmentComparison:
    segment: str
    baseline_observations: int
    candidate_observations: int
    coverage_pct: float
    baseline_average_return_pct: float | None
    candidate_average_return_pct: float | None
    candidate_median_return_pct: float | None
    candidate_positive_return_rate_pct: float | None
    uplift_vs_baseline_pct_points: float | None
    sufficient_sample: bool
    research_eligible: bool


@dataclass(frozen=True)
class CandidateExperimentReport:
    candidate: CandidateDefinition
    outcome_hours: int
    min_observations: int
    segments: tuple[CandidateSegmentComparison, ...]
    stable_positive_return: bool
    stable_positive_uplift: bool
    sufficient_sample_both: bool
    eligible_for_future_prospective_test: bool


DEFAULT_CANDIDATES = (
    CandidateDefinition(
        name="xrp_low_volume_1h",
        symbol="XRPUSDT",
        feature="volume_ratio_1h",
        operator="<=",
        value=0.75,
        description="XRPUSDT Mean Reversion WATCH BUY with 1h volume ratio <= 0.75",
    ),
    CandidateDefinition(
        name="eth_4h_lower_highs_lower_lows",
        symbol="ETHUSDT",
        feature="structure_4h",
        operator="==",
        value="lower_highs_lower_lows",
        description=(
            "ETHUSDT Mean Reversion WATCH BUY with 4h lower-highs/lower-lows structure"
        ),
    ),
)


def _median(values: Sequence[float]) -> float | None:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def _matches(snapshot: EntryFeatureSnapshot, candidate: CandidateDefinition) -> bool:
    if snapshot.symbol != candidate.symbol:
        return False
    value = getattr(snapshot, candidate.feature)
    if value is None:
        return False
    if candidate.operator == "<=":
        return float(value) <= float(candidate.value)
    if candidate.operator == "==":
        return value == candidate.value
    raise ValueError(f"unsupported candidate operator: {candidate.operator}")


class MeanReversionCandidateExperiment:
    """Research-only comparison of predefined entry candidates vs baseline.

    Candidate selection flags are derived exclusively from calibration and
    validation. The already-observed out-of-sample segment is always descriptive.
    """

    def __init__(self, *, min_observations: int = 20):
        if min_observations <= 0:
            raise ValueError("min_observations must be positive")
        self.min_observations = min_observations

    def _segment(
        self,
        *,
        segment: str,
        observations: Sequence[EntryFeatureSnapshot],
        candidate: CandidateDefinition,
    ) -> CandidateSegmentComparison:
        baseline = [item.net_return_pct for item in observations]
        selected = [
            item.net_return_pct for item in observations if _matches(item, candidate)
        ]
        baseline_avg = fmean(baseline) if baseline else None
        candidate_avg = fmean(selected) if selected else None
        eligible = segment != ValidationSegment.OUT_OF_SAMPLE.value
        return CandidateSegmentComparison(
            segment=segment,
            baseline_observations=len(baseline),
            candidate_observations=len(selected),
            coverage_pct=(len(selected) / len(baseline) * 100.0 if baseline else 0.0),
            baseline_average_return_pct=baseline_avg,
            candidate_average_return_pct=candidate_avg,
            candidate_median_return_pct=_median(selected),
            candidate_positive_return_rate_pct=(
                sum(value > 0 for value in selected) / len(selected) * 100.0
                if selected
                else None
            ),
            uplift_vs_baseline_pct_points=(
                candidate_avg - baseline_avg
                if candidate_avg is not None and baseline_avg is not None
                else None
            ),
            sufficient_sample=len(selected) >= self.min_observations,
            research_eligible=eligible,
        )

    def run(
        self,
        *,
        report: EntryQualitySymbolReport,
        candidate: CandidateDefinition,
    ) -> CandidateExperimentReport:
        if report.symbol != candidate.symbol:
            raise ValueError(
                f"candidate {candidate.name} requires {candidate.symbol}, "
                f"got {report.symbol}"
            )

        segments = tuple(
            self._segment(
                segment=segment.segment,
                observations=segment.observations,
                candidate=candidate,
            )
            for segment in report.segments
        )
        by_name = {segment.segment: segment for segment in segments}
        calibration = by_name.get(ValidationSegment.CALIBRATION.value)
        validation = by_name.get(ValidationSegment.VALIDATION.value)

        sufficient = bool(
            calibration
            and validation
            and calibration.sufficient_sample
            and validation.sufficient_sample
        )
        positive_return = bool(
            sufficient
            and calibration.candidate_average_return_pct is not None
            and validation.candidate_average_return_pct is not None
            and calibration.candidate_average_return_pct > 0
            and validation.candidate_average_return_pct > 0
        )
        positive_uplift = bool(
            sufficient
            and calibration.uplift_vs_baseline_pct_points is not None
            and validation.uplift_vs_baseline_pct_points is not None
            and calibration.uplift_vs_baseline_pct_points > 0
            and validation.uplift_vs_baseline_pct_points > 0
        )
        return CandidateExperimentReport(
            candidate=candidate,
            outcome_hours=report.outcome_hours,
            min_observations=self.min_observations,
            segments=segments,
            stable_positive_return=positive_return,
            stable_positive_uplift=positive_uplift,
            sufficient_sample_both=sufficient,
            eligible_for_future_prospective_test=bool(
                sufficient and positive_return and positive_uplift
            ),
        )

    def run_defaults(
        self,
        reports: Sequence[EntryQualitySymbolReport],
    ) -> tuple[CandidateExperimentReport, ...]:
        by_symbol = {report.symbol: report for report in reports}
        result = []
        for candidate in DEFAULT_CANDIDATES:
            report = by_symbol.get(candidate.symbol)
            if report is None:
                continue
            result.append(self.run(report=report, candidate=candidate))
        return tuple(result)
