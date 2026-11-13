from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.evaluation.candidate_discovery import bucket_for_definition
from app.evaluation.experiment_registry import ExperimentStatus, ResearchExperiment


MIN_VALIDATION_OBSERVATIONS = 20
MIN_VALIDATION_UPLIFT_PCT_POINTS = 0.10


@dataclass(frozen=True)
class ValidationReview:
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
    eligible_for_freeze_review: bool
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


def _validation_segment(report: Mapping[str, Any]) -> Mapping[str, Any]:
    for segment in report.get("segments") or []:
        if segment.get("segment") == "validation":
            return segment
    raise ValueError("validation segment not found")


def run_validation_review(
    *,
    experiment: ResearchExperiment,
    phase5f1_payload: Mapping[str, Any],
) -> ValidationReview:
    metadata = phase5f1_payload.get("metadata") or {}
    if metadata.get("phase") != "5F.1":
        raise ValueError("validation harness requires a Phase 5F.1 artifact")
    if metadata.get("research_only") is not True:
        raise ValueError("Phase 5F.1 artifact must be research_only")
    if experiment.status is not ExperimentStatus.VALIDATION:
        raise ValueError(
            "validation harness requires experiment status VALIDATION"
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
    validation = _validation_segment(report)

    row = next(
        (
            item
            for item in validation.get("buckets") or []
            if item.get("feature") == experiment.feature
            and item.get("bucket") == bucket
        ),
        None,
    )

    if row is None:
        return ValidationReview(
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
            reason="The registered rule is absent from the validation bucket summary.",
            criteria={
                "minimum_observations": False,
                "average_return_positive": None,
                "median_return_positive": None,
                "positive_return_rate_above_50": None,
                "uplift_at_least_0_10_pp": None,
            },
            eligible_for_freeze_review=False,
        )

    observations = int(row["observations"])
    average = float(row["average_return_pct"])
    median = float(row["median_return_pct"])
    positive_rate = float(row["positive_return_rate_pct"])
    baseline = float(row["baseline_return_pct"])
    uplift = float(row["uplift_vs_baseline_pct_points"])

    criteria = {
        "minimum_observations": observations >= MIN_VALIDATION_OBSERVATIONS,
        "average_return_positive": average > 0,
        "median_return_positive": median > 0,
        "positive_return_rate_above_50": positive_rate > 50.0,
        "uplift_at_least_0_10_pp": (
            uplift >= MIN_VALIDATION_UPLIFT_PCT_POINTS
        ),
    }

    if all(criteria.values()):
        decision = "PASS_VALIDATION"
        reason = (
            "All pre-registered validation criteria are satisfied. "
            "A separate human freeze review is still required."
        )
        eligible = True
    else:
        decision = "FAIL_VALIDATION"
        failed = ", ".join(
            name for name, passed in criteria.items() if passed is False
        )
        reason = f"Validation failed pre-registered criteria: {failed}."
        eligible = False

    return ValidationReview(
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
        eligible_for_freeze_review=eligible,
    )
