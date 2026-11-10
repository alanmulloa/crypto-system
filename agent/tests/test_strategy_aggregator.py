from app.strategies import (
    HypothesisDirection,
    StrategyAggregator,
    StrategyAssessment,
    StrategyState,
)


def assessment(
    strategy,
    direction,
    *,
    state=StrategyState.WATCH,
    score=80,
    confidence=75,
):
    return StrategyAssessment(
        symbol="BTCUSDT",
        strategy=strategy,
        state=state,
        direction=direction,
        score=score,
        confidence=confidence,
        timeframe="1h+4h",
    )


def rejected(strategy):
    return StrategyAssessment(
        symbol="BTCUSDT",
        strategy=strategy,
        state=StrategyState.REJECT,
        direction=None,
        score=0,
        confidence=0,
        timeframe="1h",
    )


def test_two_strong_same_direction_watch_assessments_produce_watch():
    result = StrategyAggregator().aggregate(
        (
            assessment("trend", HypothesisDirection.BUY, score=82, confidence=78),
            assessment("momentum", HypothesisDirection.BUY, score=76, confidence=70),
            rejected("mean_reversion"),
        )
    )
    assert result.state is StrategyState.WATCH
    assert result.direction is HypothesisDirection.BUY
    assert set(result.supporting_strategies) == {"trend", "momentum"}


def test_strong_opposite_conflict_forces_wait_without_direction():
    result = StrategyAggregator().aggregate(
        (
            assessment("trend", HypothesisDirection.BUY, score=80, confidence=75),
            assessment("mean_reversion", HypothesisDirection.SELL, score=78, confidence=74),
        )
    )
    assert result.state is StrategyState.WAIT
    assert result.direction is None
    assert result.conflicting_strategies


def test_single_directional_strategy_is_wait_not_watch():
    result = StrategyAggregator().aggregate(
        (
            assessment("pullback", HypothesisDirection.BUY, score=85, confidence=80),
            rejected("trend"),
            rejected("breakout"),
        )
    )
    assert result.state is StrategyState.WAIT
    assert result.direction is HypothesisDirection.BUY


def test_all_rejected_produces_reject():
    result = StrategyAggregator().aggregate((rejected("trend"), rejected("momentum")))
    assert result.state is StrategyState.REJECT
    assert result.direction is None


def test_wait_assessment_contributes_less_than_watch():
    watch_result = StrategyAggregator().aggregate(
        (
            assessment("trend", HypothesisDirection.BUY, state=StrategyState.WATCH, score=80, confidence=80),
            assessment("momentum", HypothesisDirection.BUY, state=StrategyState.WATCH, score=80, confidence=80),
        )
    )
    mixed_result = StrategyAggregator().aggregate(
        (
            assessment("trend", HypothesisDirection.BUY, state=StrategyState.WATCH, score=80, confidence=80),
            assessment("momentum", HypothesisDirection.BUY, state=StrategyState.WAIT, score=80, confidence=80),
        )
    )
    assert watch_result.state is StrategyState.WATCH
    assert mixed_result.state is StrategyState.WAIT


def test_mixed_symbols_are_rejected_as_invalid_input():
    other = StrategyAssessment(
        symbol="ETHUSDT",
        strategy="momentum",
        state=StrategyState.WATCH,
        direction=HypothesisDirection.BUY,
        score=80,
        confidence=75,
        timeframe="1h",
    )
    try:
        StrategyAggregator().aggregate(
            (assessment("trend", HypothesisDirection.BUY), other)
        )
    except ValueError:
        pass
    else:
        raise AssertionError("expected mixed-symbol aggregation to fail")
