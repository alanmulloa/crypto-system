import pytest

from app.evaluation import (
    HistoricalSanityRunner,
    OutcomeEvaluator,
    summarize_outcomes,
)
from app.market.types import Candle
from app.strategies import HypothesisDirection, StrategyState


HOUR = 60 * 60 * 1000
DAY = 24 * HOUR
INTERVAL_MS = {
    "15m": 15 * 60 * 1000,
    "1h": HOUR,
    "4h": 4 * HOUR,
    "1d": DAY,
}
CANDLES_PER_DAY = {
    "15m": 96,
    "1h": 24,
    "4h": 6,
    "1d": 1,
}


def make_series(interval: str, count: int, *, start=100.0, step=0.05):
    duration = INTERVAL_MS[interval]
    candles = []
    price = start
    for i in range(count):
        open_price = price
        close = max(1.0, price + step)
        candles.append(
            Candle(
                open_time_ms=i * duration,
                open=open_price,
                high=max(open_price, close) + 0.2,
                low=max(0.1, min(open_price, close) - 0.2),
                close=close,
                volume=1000 + i,
                close_time_ms=(i + 1) * duration - 1,
                quote_volume=(1000 + i) * close,
                trades=100 + i,
            )
        )
        price = close
    return candles


def market_history(days=100):
    return {
        interval: make_series(interval, days * CANDLES_PER_DAY[interval])
        for interval in ("15m", "1h", "4h", "1d")
    }


def one_point_with_future():
    history = market_history(100)
    runner = HistoricalSanityRunner(min_candles=60)
    cutoff = 80 * DAY - 1
    candidate = runner.build_candidate(
        symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
        candles_by_interval=history,
        timestamp_ms=cutoff,
    )
    assert candidate is not None
    assessments = runner.strategy_engine.evaluate(candidate)
    aggregate = runner.aggregator.aggregate(assessments)
    from app.evaluation.historical import HistoricalPoint

    return history, HistoricalPoint(
        timestamp_ms=cutoff,
        candidate=candidate,
        assessments=assessments,
        aggregate=aggregate,
    )


def test_outcomes_use_only_candles_strictly_after_signal():
    history, point = one_point_with_future()
    evaluator = OutcomeEvaluator(horizons_ms={"4h": 4 * HOUR})
    observations = evaluator.evaluate_point(point=point, candles_by_interval=history)
    aggregate = observations[0]
    window = aggregate.window_for("4h")
    assert window is not None

    future = [
        candle for candle in history["1h"]
        if point.timestamp_ms < candle.close_time_ms <= window.observed_timestamp_ms
    ]
    assert future
    assert all(candle.close_time_ms > point.timestamp_ms for candle in future)
    assert window.exit_price == future[-1].close


def test_directional_buy_metrics_are_oriented_correctly():
    evaluator = OutcomeEvaluator()
    directional, mfe, mae = evaluator._directional_metrics(
        direction=HypothesisDirection.BUY,
        raw_return_pct=5,
        max_up_pct=8,
        max_down_pct=-3,
    )
    assert directional == 5
    assert mfe == 8
    assert mae == 3


def test_directional_sell_metrics_are_oriented_correctly():
    evaluator = OutcomeEvaluator()
    directional, mfe, mae = evaluator._directional_metrics(
        direction=HypothesisDirection.SELL,
        raw_return_pct=-5,
        max_up_pct=2,
        max_down_pct=-9,
    )
    assert directional == 5
    assert mfe == 9
    assert mae == 2


def test_directionless_wait_or_reject_keeps_raw_market_path():
    history, point = one_point_with_future()
    evaluator = OutcomeEvaluator(horizons_ms={"4h": 4 * HOUR})
    observations = evaluator.evaluate_point(point=point, candles_by_interval=history)
    directionless = next(
        (
            observation
            for observation in observations
            if observation.direction is None
        ),
        None,
    )
    if directionless is None:
        pytest.skip("current deterministic fixture produced no directionless observation")

    window = directionless.window_for("4h")
    assert window is not None
    assert window.directional_return_pct is None
    assert window.mfe_pct is None
    assert window.mae_pct is None
    assert window.max_up_pct >= window.max_down_pct


def test_missing_future_horizon_is_omitted_not_fabricated():
    history, point = one_point_with_future()
    last_point = point.__class__(
        timestamp_ms=history["1h"][-2].close_time_ms,
        candidate=point.candidate,
        assessments=point.assessments,
        aggregate=point.aggregate,
    )
    evaluator = OutcomeEvaluator(horizons_ms={"3d": 3 * DAY})
    observations = evaluator.evaluate_point(point=last_point, candles_by_interval=history)
    assert observations
    assert all(observation.windows == () for observation in observations)


def test_summary_can_compare_watch_and_rejected_observations():
    history = market_history(100)
    runner = HistoricalSanityRunner(min_candles=60)
    points = runner.run(
        symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
        candles_by_interval=history,
        max_points=200,
    )
    observations = OutcomeEvaluator(horizons_ms={"4h": 4 * HOUR}).evaluate_points(
        points=points,
        candles_by_interval=history,
    )
    watch = summarize_outcomes(
        observations,
        horizon="4h",
        source="strategy",
        state=StrategyState.WATCH,
    )
    rejected = summarize_outcomes(
        observations,
        horizon="4h",
        source="strategy",
        state=StrategyState.REJECT,
    )
    assert watch.observations >= 0
    assert rejected.observations >= 0
    assert watch.observations + rejected.observations <= len(observations)


def test_summary_directional_hit_rate_is_bounded():
    history = market_history(100)
    runner = HistoricalSanityRunner(min_candles=60)
    points = runner.run(
        symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
        candles_by_interval=history,
        max_points=100,
    )
    observations = OutcomeEvaluator(horizons_ms={"4h": 4 * HOUR}).evaluate_points(
        points=points,
        candles_by_interval=history,
    )
    summary = summarize_outcomes(
        observations,
        horizon="4h",
        source="strategy",
    )
    if summary.directional_hit_rate_pct is not None:
        assert 0 <= summary.directional_hit_rate_pct <= 100
