from app.evaluation import HistoricalSanityRunner, summarize
from app.market.types import Candle


INTERVAL_MS = {
    "15m": 15 * 60 * 1000,
    "1h": 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
    "1d": 24 * 60 * 60 * 1000,
}

CANDLES_PER_DAY = {
    "15m": 96,
    "1h": 24,
    "4h": 6,
    "1d": 1,
}


def make_series(interval: str, count: int, *, start=100.0, step=0.02, shock_after_ms=None):
    duration = INTERVAL_MS[interval]
    candles = []
    price = start
    for i in range(count):
        close_time_ms = (i + 1) * duration - 1
        local_step = step
        if shock_after_ms is not None and close_time_ms > shock_after_ms:
            local_step = -1.0
        open_price = price
        close = max(1.0, price + local_step)
        high = max(open_price, close) + 0.15
        low = max(0.1, min(open_price, close) - 0.15)
        candles.append(
            Candle(
                open_time_ms=i * duration,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=1000 + i * 0.5,
                close_time_ms=close_time_ms,
                quote_volume=(1000 + i * 0.5) * close,
                trades=100 + i,
            )
        )
        price = close
    return candles


def market_history(days=90, *, shock_after_ms=None):
    return {
        interval: make_series(
            interval,
            days * CANDLES_PER_DAY[interval],
            shock_after_ms=shock_after_ms,
        )
        for interval in ("15m", "1h", "4h", "1d")
    }


def test_future_candles_do_not_change_assessment_at_existing_timestamp():
    runner = HistoricalSanityRunner(min_candles=60)
    history = market_history(90)
    cutoff = 70 * INTERVAL_MS["1d"] - 1

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

    shocked = market_history(90, shock_after_ms=cutoff)
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
    history = market_history(70)
    points = runner.run(
        symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
        candles_by_interval=history,
        max_points=50,
    )
    assert points
    for point in points:
        assert all(item.candles >= 60 for item in point.candidate.analyses)
        assert all(item.candles <= 250 for item in point.candidate.analyses)


def test_runner_is_deterministic():
    runner = HistoricalSanityRunner(min_candles=60)
    history = market_history(70)
    kwargs = dict(
        symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
        candles_by_interval=history,
        max_points=20,
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
        candles_by_interval=market_history(70),
        max_points=20,
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
    history = market_history(70)
    history.pop("1d")
    candidate = runner.build_candidate(
        symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
        candles_by_interval=history,
        timestamp_ms=history["1h"][-1].close_time_ms,
    )
    assert candidate is None


def test_historical_window_matches_live_default_depth():
    runner = HistoricalSanityRunner(min_candles=60, analysis_candles=250)
    history = market_history(90)
    candidate = runner.build_candidate(
        symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
        candles_by_interval=history,
        timestamp_ms=history["1h"][-1].close_time_ms,
    )
    assert candidate is not None
    assert candidate.analysis_for("15m").candles == 250
    assert candidate.analysis_for("1h").candles == 250
    assert candidate.analysis_for("4h").candles == 250
    assert candidate.analysis_for("1d").candles == 90
