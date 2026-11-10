from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from app.evaluation.historical import HistoricalPoint
from app.strategies.base import StrategyState


@dataclass(frozen=True)
class StrategyStateCounts:
    strategy: str
    watch: int
    wait: int
    reject: int


@dataclass(frozen=True)
class HistoricalSanityReport:
    points: int
    aggregate_watch: int
    aggregate_wait: int
    aggregate_reject: int
    unresolved_conflicts: int
    per_strategy: tuple[StrategyStateCounts, ...]


def summarize(points: tuple[HistoricalPoint, ...]) -> HistoricalSanityReport:
    aggregate_counts = Counter(point.aggregate.state for point in points)
    unresolved_conflicts = sum(
        point.aggregate.state is StrategyState.WAIT
        and point.aggregate.direction is None
        and bool(point.aggregate.conflicting_strategies)
        for point in points
    )

    strategy_names = sorted(
        {assessment.strategy for point in points for assessment in point.assessments}
    )
    per_strategy: list[StrategyStateCounts] = []
    for name in strategy_names:
        counts = Counter(
            assessment.state
            for point in points
            for assessment in point.assessments
            if assessment.strategy == name
        )
        per_strategy.append(
            StrategyStateCounts(
                strategy=name,
                watch=counts[StrategyState.WATCH],
                wait=counts[StrategyState.WAIT],
                reject=counts[StrategyState.REJECT],
            )
        )

    return HistoricalSanityReport(
        points=len(points),
        aggregate_watch=aggregate_counts[StrategyState.WATCH],
        aggregate_wait=aggregate_counts[StrategyState.WAIT],
        aggregate_reject=aggregate_counts[StrategyState.REJECT],
        unresolved_conflicts=unresolved_conflicts,
        per_strategy=tuple(per_strategy),
    )
