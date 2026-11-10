from dataclasses import replace

from app.evaluation.diagnostics import (
    DiagnosticConfig,
    StrategyDiagnostics,
    interval_quality,
)
from app.evaluation.historical import HistoricalPoint
from app.evaluation.validation import TemporalSplitConfig, ValidationSegment
from app.market.types import (
    Candle,
    IndicatorSnapshot,
    MarketCandidate,
    MarketRegime,
    TimeframeAnalysis,
)
from app.strategies import (
    AggregatedAssessment,
    HypothesisDirection,
    StrategyAssessment,
    StrategyState,
)


HOUR = 60 * 60 * 1000


def candle(index, *, open_price=100, high=101, low=99, close=100):
    return Candle(
        open_time_ms=index * HOUR,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=1000,
        close_time_ms=(index + 1) * HOUR - 1,
    )


def candidate(*, symbol="BTCUSDT", atr=2.0, regime=MarketRegime.RANGING):
    indicator = IndicatorSnapshot(
        ema_fast=100,
        ema_slow=100,
        rsi=35,
        atr=atr,
        atr_pct=2,
        volume_ratio=1,
        structure="range",
    )
    h1 = TimeframeAnalysis(
        interval="1h",
        candles=100,
        last_price=100,
        indicators=indicator,
        regime=regime,
    )
    h4 = replace(h1, interval="4h")
    return MarketCandidate(
        symbol=symbol,
        base_asset=symbol.replace("USDT", ""),
        quote_asset="USDT",
        quote_volume_24h=1_000_000,
        price_change_pct_24h=0,
        trade_count_24h=10_000,
        analyses=(h1, h4),
    )


def assessment(
    *,
    symbol="BTCUSDT",
    direction=HypothesisDirection.BUY,
    state=StrategyState.WATCH,
    stop=98,
    tp1=104,
):
    return StrategyAssessment(
        symbol=symbol,
        strategy="mean_reversion",
        state=state,
        direction=direction if state is not StrategyState.REJECT else None,
        score=80 if state is not StrategyState.REJECT else 0,
        confidence=75 if state is not StrategyState.REJECT else 0,
        timeframe="1h+4h",
        entry_low=95 if state is not StrategyState.REJECT else None,
        entry_high=105 if state is not StrategyState.REJECT else None,
        stop=stop if state is not StrategyState.REJECT else None,
        tp1=tp1 if state is not StrategyState.REJECT else None,
    )


def point(index, item=None, *, symbol="BTCUSDT", regime=MarketRegime.RANGING):
    item = item or assessment(symbol=symbol)
    aggregate = AggregatedAssessment(
        symbol=symbol,
        state=item.state,
        direction=item.direction,
        score=item.score,
        confidence=item.confidence,
        supporting_strategies=(item.strategy,) if item.direction else (),
    )
    return HistoricalPoint(
        timestamp_ms=(index + 1) * HOUR - 1,
        candidate=candidate(symbol=symbol, regime=regime),
        assessments=(item,),
        aggregate=aggregate,
    )


def analyzer(*, fees=0, slippage=0):
    return StrategyDiagnostics(
        DiagnosticConfig(
            fee_bps=fees,
            slippage_bps=slippage,
            require_entry_range=True,
            significant_mfe_pct=0.5,
        ),
        split_config=TemporalSplitConfig(
            calibration_ratio=0.6,
            validation_ratio=0.2,
            out_of_sample_ratio=0.2,
            min_points_per_segment=2,
        ),
    )


def test_mfe_mae_and_times_use_only_future_path():
    candles = [
        candle(0),
        candle(1, open_price=100, high=101, low=99, close=100),
        candle(2, open_price=100, high=105, low=98, close=104),
        candle(3, open_price=104, high=104, low=97, close=99),
    ]
    item = analyzer()._prepare(
        strategy="mean_reversion",
        segment=ValidationSegment.CALIBRATION,
        point=point(0),
        candles=candles,
    )
    assert item is not None
    assert item.public.mfe_pct == 5.0
    assert item.public.mae_pct == 3.0
    assert item.public.time_to_mfe_ms == 2 * HOUR - 1
    assert item.public.time_to_mae_ms == 3 * HOUR - 1


def test_no_lookahead_before_signal_is_ignored():
    candles = [
        candle(0, open_price=100, high=500, low=1, close=100),
        candle(1, open_price=100, high=101, low=99, close=100),
        candle(2, open_price=100, high=102, low=98, close=101),
    ]
    item = analyzer()._prepare(
        strategy="mean_reversion",
        segment=ValidationSegment.CALIBRATION,
        point=point(0),
        candles=candles,
    )
    assert item is not None
    assert item.public.mfe_pct == 2.0
    assert item.public.mae_pct == 2.0


def test_partial_horizons_are_not_fabricated():
    candles = [
        candle(0),
        candle(1),
        candle(2),
        candle(3),
    ]
    item = analyzer()._prepare(
        strategy="mean_reversion",
        segment=ValidationSegment.CALIBRATION,
        point=point(0),
        candles=candles,
    )
    assert item is not None
    hours = {snapshot.horizon_hours for snapshot in item.public.horizons}
    assert 1 in hours
    assert 2 in hours
    assert 4 not in hours
    assert 48 not in hours


def test_fees_and_slippage_reduce_fixed_horizon_return():
    clean = analyzer()
    costly = analyzer(fees=10, slippage=5)
    clean_return = clean._net_trade(100, 102)[1]
    costly_return = costly._net_trade(100, 102)[1]
    assert clean_return == 2.0
    assert costly_return < clean_return


def test_current_exit_preserves_stop_first_intrabar_rule():
    candles = [
        candle(0),
        candle(1, open_price=100, high=105, low=97, close=101),
    ]
    item = analyzer()._prepare(
        strategy="mean_reversion",
        segment=ValidationSegment.CALIBRATION,
        point=point(0, assessment(stop=98, tp1=104)),
        candles=candles,
    )
    assert item is not None
    assert item.public.current_exit_reason == "STOP"
    assert item.public.intrabar_ambiguous is True


def test_fixed_horizon_exit_is_reported():
    candles = [candle(0)]
    for index in range(1, 8):
        candles.append(
            candle(
                index,
                open_price=100,
                high=101 + index,
                low=99,
                close=100 + index,
            )
        )
    item = analyzer()._prepare(
        strategy="mean_reversion",
        segment=ValidationSegment.CALIBRATION,
        point=point(0, assessment(stop=50, tp1=200)),
        candles=candles,
    )
    assert item is not None
    scenarios = analyzer()._fixed_horizon_scenarios(
        [item],
        ValidationSegment.CALIBRATION,
    )
    fixed4 = next(row for row in scenarios if row.name == "fixed_4h")
    assert fixed4.observations == 1
    assert fixed4.avg_return_pct is not None
    assert fixed4.avg_return_pct > 0


def test_atr_stop_target_sensitivity_uses_point_atr():
    candles = [
        candle(0),
        candle(1, open_price=100, high=103, low=99.5, close=102),
    ]
    item = analyzer()._prepare(
        strategy="mean_reversion",
        segment=ValidationSegment.CALIBRATION,
        point=point(0, assessment(stop=50, tp1=200)),
        candles=candles,
    )
    assert item is not None
    result = analyzer()._atr_return(item, stop_atr=1.0, target_atr=1.0)
    assert result == 2.0


def test_sell_is_never_converted_to_short():
    sell = assessment(direction=HypothesisDirection.SELL, stop=105, tp1=95)
    points = [point(index, sell) for index in range(10)]
    candles = [candle(index) for index in range(20)]
    report = analyzer().run_symbol(
        strategy="mean_reversion",
        points=points,
        candles_by_interval={"1h": candles},
    )
    assert report.skipped_sell == 10
    assert all(not segment.paths for segment in report.segments)


def test_segment_isolation_omits_future_horizons_at_boundary():
    points = [point(index) for index in range(10)]
    candles = [candle(index) for index in range(20)]
    report = analyzer().run_symbol(
        strategy="mean_reversion",
        points=points,
        candles_by_interval={"1h": candles},
    )
    calibration = report.segments[0]
    assert calibration.segment == "calibration"
    assert calibration.paths
    last = calibration.paths[-1]
    assert all(snapshot.horizon_hours < 4 for snapshot in last.horizons)


def test_groups_include_symbol_regime_and_segment():
    candles = [candle(index) for index in range(20)]
    report = analyzer().run_symbol(
        strategy="mean_reversion",
        points=[point(index) for index in range(10)],
        candles_by_interval={"1h": candles},
    )
    dimensions = {
        group.dimension
        for segment in report.segments
        for group in segment.group_summaries
    }
    assert {"strategy", "symbol", "regime", "segment"} <= dimensions


def test_output_is_deterministic():
    kwargs = dict(
        strategy="mean_reversion",
        points=[point(index) for index in range(10)],
        candles_by_interval={"1h": [candle(index) for index in range(20)]},
    )
    first = analyzer().run_symbol(**kwargs)
    second = analyzer().run_symbol(**kwargs)
    assert first == second


def test_historical_objects_are_not_mutated():
    original_point = point(0)
    original_assessment = original_point.assessments[0]
    candles = [candle(index) for index in range(5)]
    analyzer()._prepare(
        strategy="mean_reversion",
        segment=ValidationSegment.CALIBRATION,
        point=original_point,
        candles=candles,
    )
    assert original_point.assessments[0] == original_assessment


def test_exit_analysis_counts_favorable_loss_and_recovery():
    candles = [
        candle(0),
        candle(1, open_price=100, high=101, low=97, close=98),
        candle(2, open_price=98, high=103, low=97, close=102),
    ]
    item = analyzer()._prepare(
        strategy="mean_reversion",
        segment=ValidationSegment.CALIBRATION,
        point=point(0, assessment(stop=98, tp1=110)),
        candles=candles,
    )
    assert item is not None
    summary = analyzer()._current_exit_analysis([item.public])
    assert summary.favorable_then_loss == 1
    assert summary.stop_before_later_recovery == 1


def test_interval_quality_detects_gap_and_duplicate():
    candles = [
        candle(0),
        candle(1),
        candle(1),
        candle(3),
    ]
    quality = interval_quality("1h", candles)
    assert quality.duplicate_open_times == 1
    assert quality.gap_count == 1


def test_oos_atr_rows_are_marked_not_research_eligible():
    candles = [
        candle(0),
        candle(1, open_price=100, high=103, low=99, close=102),
    ]
    item = analyzer()._prepare(
        strategy="mean_reversion",
        segment=ValidationSegment.OUT_OF_SAMPLE,
        point=point(0, assessment(stop=50, tp1=200)),
        candles=candles,
    )
    assert item is not None
    rows = analyzer()._atr_sensitivity(
        [item],
        ValidationSegment.OUT_OF_SAMPLE,
    )
    assert rows
    assert all(row.research_eligible is False for row in rows)
