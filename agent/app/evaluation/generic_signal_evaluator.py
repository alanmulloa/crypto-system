from __future__ import annotations

from app.evaluation.historical import HistoricalPoint
from app.evaluation.prospective_bootstrap import GenericProspectiveProtocol
from app.market.types import TimeframeAnalysis
from app.strategies.base import StrategyAssessment, StrategyState


def assessment_for(
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


def _analysis(point: HistoricalPoint, interval: str) -> TimeframeAnalysis | None:
    return point.candidate.analysis_for(interval)


def _ema_distance_pct(analysis: TimeframeAnalysis) -> float:
    ema = analysis.indicators.ema_fast
    return 0.0 if ema == 0 else (analysis.last_price / ema - 1.0) * 100.0


def _ema_spread_pct(analysis: TimeframeAnalysis) -> float:
    slow = analysis.indicators.ema_slow
    if slow == 0:
        return 0.0
    return (analysis.indicators.ema_fast / slow - 1.0) * 100.0


def feature_value(
    point: HistoricalPoint,
    *,
    strategy: str,
    feature: str,
) -> float | str | None:
    assessment = assessment_for(point, strategy)
    if feature == "score":
        return assessment.score if assessment is not None else None
    if feature == "confidence":
        return assessment.confidence if assessment is not None else None

    mapping = {
        "rsi_1h": ("1h", "rsi"),
        "atr_pct_1h": ("1h", "atr_pct"),
        "volume_ratio_1h": ("1h", "volume_ratio"),
        "rsi_15m": ("15m", "rsi"),
        "rsi_4h": ("4h", "rsi"),
        "structure_1h": ("1h", "structure"),
        "structure_4h": ("4h", "structure"),
    }
    if feature in mapping:
        interval, field = mapping[feature]
        analysis = _analysis(point, interval)
        return (
            getattr(analysis.indicators, field)
            if analysis is not None
            else None
        )

    if feature.startswith("ema_distance_pct_"):
        interval = feature.removeprefix("ema_distance_pct_")
        analysis = _analysis(point, interval)
        return _ema_distance_pct(analysis) if analysis is not None else None

    if feature == "ema_spread_pct_1h":
        analysis = _analysis(point, "1h")
        return _ema_spread_pct(analysis) if analysis is not None else None

    raise ValueError(f"unsupported generic prospective feature: {feature}")


def evaluate_operator(
    value: float | str,
    operator: str,
    threshold: float | int | str,
) -> bool:
    if operator == "==":
        return value == threshold
    if isinstance(value, str) or isinstance(threshold, str):
        raise ValueError("ordered operators require numeric values")
    left = float(value)
    right = float(threshold)
    if operator == "<=":
        return left <= right
    if operator == ">=":
        return left >= right
    if operator == "<":
        return left < right
    if operator == ">":
        return left > right
    raise ValueError(f"unsupported operator: {operator}")


def baseline_matches(
    point: HistoricalPoint,
    *,
    protocol: GenericProspectiveProtocol,
) -> bool:
    if point.candidate.symbol != protocol.symbol:
        return False
    assessment = assessment_for(point, protocol.strategy)
    return bool(
        assessment is not None
        and assessment.state is StrategyState.WATCH
        and assessment.direction is not None
        and assessment.direction.value == protocol.direction
    )


def candidate_matches(
    point: HistoricalPoint,
    *,
    protocol: GenericProspectiveProtocol,
) -> bool:
    if not baseline_matches(point, protocol=protocol):
        return False
    value = feature_value(
        point,
        strategy=protocol.strategy,
        feature=protocol.feature,
    )
    if value is None:
        return False
    return evaluate_operator(value, protocol.operator, protocol.threshold)
