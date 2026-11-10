from app.evaluation import HistoricalSanityRunner, summarize
from app.market.types import Candle


INTERVAL_MS = {
    "15m": 15 * 60 * 1000,
    "1h": 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
    "1d": 24 * 60 * 60 * 1000,
}


def make_series(interval: str, count: int, *, start=100.0, step=0.25, future_shock_at=None):
    duration = INTERVAL_MS[interval]
    candles = []
    price = start
    for i in range(count):
        local_step = step
        if future_shock_at is not None and i >= future_shock_at:
            local_step = -5.0
        open_price = price
        close = max(1.0, price + local_step)
        high = max(open_price, close) + 0.6
        low = max(0.1, min(open_price, close) - 0.6)
        candles.append(
            Candle(
                open_time_ms=i * duration,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=1000 + i * 3,
                close_time_ms=(i + 1) * duration - 1,
                quote_volume=(1000 + i * 3) * close,
                trades=100 + i,
            )
        )
        price = close
    return candles


def market_history(count=180, *, future_shock_at=None):
    return {
        interval: make_series(
            interval,
            count,
            future_shock_at=future_shock_at,
        )
        for interval in ("15m", "1h", "4h", "1d")
    }


def test_future_candles_do_not_change_assessment_at_existing_timestamp():
    runner = HistoricalSanityRunner(min_candles=60)
    history = market_history(180)
    cutoff = history["1h"][100].close_time_ms

    baseline = runner.build_candidate(
        symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
        candles_by_interval=history,
        timestamp_ms=cutoff,
    )
    assert baseline is not None
    baseline_assessments = runner.strategy_engine.evaluate(baseline)
    baseline_aggregate = runner.aggregator.aggregate(baseline_assessments)

    shocked = market_history(180, future_shock_at=120)
    changed_future = runner.build_candidate(
        symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
        candles_by_interval=shocked,
        timestamp_ms=cutoff,
    )
    assert changed_future is not None
    changed_assessments = runner.strategy_engine.evaluate(changed_future)
    changed_aggregate = runner.aggregator.aggregate(changed_assessments)

    assert changed_future == baseline
    assert changed_assessments == baseline_assessments
    assert changed_aggregate == baseline_aggregate


def test_runner_only_emits_points_after_all_timeframes_have_warmup():
    runner = HistoricalSanityRunner(min_candles=60)
    history = market_history(100)
    points = runner.run(
        symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
        candles_by_interval=history,
    )
    assert points
    for point in points:
        assert all(item.candles >= 60 for item in point.candidate.analyses)


def test_runner_is_deterministic():
    runner = HistoricalSanityRunner(min_candles=60)
    history = market_history(120)
    kwargs = dict(
        symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
        candles_by_interval=history,
        max_points=30,
    )
    first = runner.run(**kwargs)
    second = runner.run(**kwargs)
    assert first == second


def test_summary_counts_all_points_and_strategies():
    runner = HistoricalSanityRunner(min_candles=60)
    points = runner.run(
        symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
        candles_by_interval=market_history(120),
        max_points=25,
    )
    report = summarize(points)
    assert report.points == len(points)
    assert report.aggregate_watch + report.aggregate_wait + report.aggregate_reject == report.points
    assert {item.strategy for item in report.per_strategy} == {
        "breakout",
        "mean_reversion",
        "momentum",
        "pullback",
        "trend_following",
    }
    for item in report.per_strategy:
        assert item.watch + item.wait + item.reject == report.points


def test_missing_timeframe_produces_no_candidate():
    runner = HistoricalSanityRunner(min_candles=60)
    history = market_history(100)
    history.pop("1d")
    candidate = runner.build_candidate(
        symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
        candles_by_interval=history,
        timestamp_ms=history["1h"][-1].close_time_ms,
    )
    assert candidate is None
