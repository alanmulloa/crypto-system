from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.evaluation.candidate_discovery import bucket_for_definition
from app.evaluation.experiment_registry import (
    ExperimentStatus,
    ResearchExperiment,
)


MIN_CALIBRATION_OBSERVATIONS = 20


@dataclass(frozen=True)
class CalibrationReview:
    experiment_id: str
    symbol: str
    strategy: str
    feature: str
    operator: str
    threshold: float | int | str
    bucket: str
    observations: int
    average_return_pct: float | None
    median_return_pct: float | None
    positive_return_rate_pct: float | None
    baseline_return_pct: float | None
    uplift_vs_baseline_pct_points: float | None
    decision: str
    reason: str
    criteria: Mapping[str, bool | None]
    eligible_for_validation: bool
    auto_transition: bool = False
    research_only: bool = True
    phase6_blocked: bool = True


def _symbol_report(
    payload: Mapping[str, Any],
    experiment: ResearchExperiment,
) -> Mapping[str, Any]:
    for report in payload.get("results") or []:
        if (
            str(report.get("symbol")) == experiment.symbol
            and str(report.get("strategy")) == experiment.strategy
            and int(report.get("outcome_hours")) == experiment.outcome_hours
        ):
            return report
    raise ValueError("matching Phase 5F.1 symbol report not found")


def _calibration_segment(report: Mapping[str, Any]) -> Mapping[str, Any]:
    for segment in report.get("segments") or []:
        if segment.get("segment") == "calibration":
            return segment
    raise ValueError("calibration segment not found")


def run_calibration_review(
    *,
    experiment: ResearchExperiment,
    phase5f1_payload: Mapping[str, Any],
) -> CalibrationReview:
    metadata = phase5f1_payload.get("metadata") or {}
    if metadata.get("phase") != "5F.1":
        raise ValueError("calibration harness requires a Phase 5F.1 artifact")
    if metadata.get("research_only") is not True:
        raise ValueError("Phase 5F.1 artifact must be research_only")
    if experiment.status is not ExperimentStatus.CALIBRATION:
        raise ValueError(
            "calibration harness requires experiment status CALIBRATION"
        )

    bucket = bucket_for_definition(
        feature=experiment.feature,
        operator=experiment.operator,
        threshold=experiment.threshold,
    )
    if bucket is None:
        raise ValueError(
            "experiment definition does not map to a pre-defined Phase 5F.1 bucket"
        )

    report = _symbol_report(phase5f1_payload, experiment)
    calibration = _calibration_segment(report)

    row = next(
        (
            item
            for item in calibration.get("buckets") or []
            if item.get("feature") == experiment.feature
            and item.get("bucket") == bucket
        ),
        None,
    )

    if row is None:
        return CalibrationReview(
            experiment_id=experiment.id,
            symbol=experiment.symbol,
            strategy=experiment.strategy,
            feature=experiment.feature,
            operator=experiment.operator,
            threshold=experiment.threshold,
            bucket=bucket,
            observations=0,
            average_return_pct=None,
            median_return_pct=None,
            positive_return_rate_pct=None,
            baseline_return_pct=None,
            uplift_vs_baseline_pct_points=None,
            decision="INCONCLUSIVE",
            reason="The registered rule is absent from the calibration bucket summary.",
            criteria={
                "minimum_observations": False,
                "average_return_positive": None,
                "median_return_positive": None,
                "positive_return_rate_above_50": None,
                "uplift_positive": None,
            },
            eligible_for_validation=False,
        )

    observations = int(row["observations"])
    average = float(row["average_return_pct"])
    median = float(row["median_return_pct"])
    positive_rate = float(row["positive_return_rate_pct"])
    baseline = float(row["baseline_return_pct"])
    uplift = float(row["uplift_vs_baseline_pct_points"])

    criteria = {
        "minimum_observations": observations >= MIN_CALIBRATION_OBSERVATIONS,
        "average_return_positive": average > 0,
        "median_return_positive": median > 0,
        "positive_return_rate_above_50": positive_rate > 50.0,
        "uplift_positive": uplift > 0,
    }

    if all(criteria.values()):
        decision = "PASS_CALIBRATION"
        reason = (
            "All pre-registered calibration criteria are satisfied. "
            "A separate explicit transition is required before validation."
        )
        eligible = True
    else:
        decision = "FAIL_CALIBRATION"
        failed = ", ".join(
            name for name, passed in criteria.items() if passed is False
        )
        reason = f"Calibration failed pre-registered criteria: {failed}."
        eligible = False

    return CalibrationReview(
        experiment_id=experiment.id,
        symbol=experiment.symbol,
        strategy=experiment.strategy,
        feature=experiment.feature,
        operator=experiment.operator,
        threshold=experiment.threshold,
        bucket=bucket,
        observations=observations,
        average_return_pct=average,
        median_return_pct=median,
        positive_return_rate_pct=positive_rate,
        baseline_return_pct=baseline,
        uplift_vs_baseline_pct_points=uplift,
        decision=decision,
        reason=reason,
        criteria=criteria,
        eligible_for_validation=eligible,
    )
