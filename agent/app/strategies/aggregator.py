from __future__ import annotations

from dataclasses import dataclass, field

from app.strategies.base import HypothesisDirection, StrategyAssessment, StrategyState


@dataclass(frozen=True)
class AggregatedAssessment:
    symbol: str
    state: StrategyState
    direction: HypothesisDirection | None
    score: float
    confidence: float
    supporting_strategies: tuple[str, ...] = field(default_factory=tuple)
    conflicting_strategies: tuple[str, ...] = field(default_factory=tuple)
    rejected_strategies: tuple[str, ...] = field(default_factory=tuple)
    reasons: tuple[str, ...] = field(default_factory=tuple)


_STATE_WEIGHT = {
    StrategyState.WATCH: 1.0,
    StrategyState.WAIT: 0.35,
    StrategyState.REJECT: 0.0,
}


def _strength(item: StrategyAssessment) -> float:
    if item.direction is None:
        return 0.0
    return item.score * (item.confidence / 100.0) * _STATE_WEIGHT[item.state]


class StrategyAggregator:
    """Phase 2B conflict-aware research aggregator.

    This module produces a research state only. It does not call the Risk Manager,
    calculate position sizing, access brokers, or create executable orders.
    """

    def aggregate(self, assessments: tuple[StrategyAssessment, ...]) -> AggregatedAssessment:
        if not assessments:
            raise ValueError("at least one strategy assessment is required")

        symbols = {item.symbol for item in assessments}
        if len(symbols) != 1:
            raise ValueError("all assessments must belong to the same symbol")
        symbol = next(iter(symbols))

        directional = [item for item in assessments if item.direction is not None and item.state is not StrategyState.REJECT]
        rejected = tuple(item.strategy for item in assessments if item.state is StrategyState.REJECT)

        if not directional:
            return AggregatedAssessment(
                symbol=symbol,
                state=StrategyState.REJECT,
                direction=None,
                score=0.0,
                confidence=0.0,
                rejected_strategies=rejected,
                reasons=("no strategy produced a viable directional hypothesis",),
            )

        groups: dict[HypothesisDirection, list[StrategyAssessment]] = {
            HypothesisDirection.BUY: [],
            HypothesisDirection.SELL: [],
        }
        for item in directional:
            groups[item.direction].append(item)

        support = {
            direction: sum(_strength(item) for item in items)
            for direction, items in groups.items()
        }
        winner = max(support, key=support.get)
        loser = HypothesisDirection.SELL if winner is HypothesisDirection.BUY else HypothesisDirection.BUY
        winner_support = support[winner]
        loser_support = support[loser]

        winner_items = groups[winner]
        loser_items = groups[loser]

        if winner_support <= 0:
            return AggregatedAssessment(
                symbol=symbol,
                state=StrategyState.REJECT,
                direction=None,
                score=0.0,
                confidence=0.0,
                rejected_strategies=rejected,
                reasons=("strategy support is insufficient",),
            )

        conflict_ratio = loser_support / winner_support if winner_support else 0.0
        supporting_names = tuple(item.strategy for item in winner_items)
        conflicting_names = tuple(item.strategy for item in loser_items)

        weighted_score_numerator = sum(item.score * _strength(item) for item in winner_items)
        weighted_conf_numerator = sum(item.confidence * _strength(item) for item in winner_items)
        weighted_denominator = sum(_strength(item) for item in winner_items)
        score = weighted_score_numerator / weighted_denominator if weighted_denominator else 0.0
        confidence = weighted_conf_numerator / weighted_denominator if weighted_denominator else 0.0

        reasons = [
            f"{len(winner_items)} strategy assessment(s) support {winner.value}",
            f"directional support strength {winner_support:.1f}",
        ]

        if loser_items:
            reasons.append(
                f"{len(loser_items)} conflicting assessment(s) support {loser.value} "
                f"(conflict ratio {conflict_ratio:.2f})"
            )

        # Strong unresolved conflict: do not expose a direction as actionable research.
        if conflict_ratio >= 0.65:
            return AggregatedAssessment(
                symbol=symbol,
                state=StrategyState.WAIT,
                direction=None,
                score=score,
                confidence=min(confidence, 55.0),
                supporting_strategies=supporting_names,
                conflicting_strategies=conflicting_names,
                rejected_strategies=rejected,
                reasons=tuple(reasons + ["directional conflict is too strong to prefer one side"]),
            )

        watch_count = sum(item.state is StrategyState.WATCH for item in winner_items)
        strong_watch = watch_count >= 2 and score >= 70 and confidence >= 60

        if strong_watch:
            state = StrategyState.WATCH
            reasons.append("multiple WATCH assessments support the same direction")
        else:
            state = StrategyState.WAIT
            reasons.append("evidence is directional but not strong enough for WATCH")

        return AggregatedAssessment(
            symbol=symbol,
            state=state,
            direction=winner,
            score=max(0.0, min(100.0, score)),
            confidence=max(0.0, min(100.0, confidence)),
            supporting_strategies=supporting_names,
            conflicting_strategies=conflicting_names,
            rejected_strategies=rejected,
            reasons=tuple(reasons),
        )
