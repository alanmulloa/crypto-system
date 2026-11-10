from dataclasses import replace

import pytest

from app.evaluation.entry_quality import (
    MeanReversionEntryDiagnostics,
    _numeric_bucket,
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


def candle(index, *, close=100):
    return Candle(
        open_time_ms=index * HOUR,
        open=100,
        high=max(101, close),
        low=min(99, close),
        close=close,
        volume=1000,
        close_time_ms=(index + 1) * HOUR - 1,
    )


def analysis(interval, *, rsi=30, atr_pct=2, price=98, ema_fast=100, ema_slow=101):
    return TimeframeAnalysis(
        interval=interval,
        candles=100,
        last_price=price,
        indicators=IndicatorSnapshot(
            ema_fast=ema_fast,
            ema_slow=ema_slow,
            rsi=rsi,
            atr=2,
            atr_pct=atr_pct,
            volume_ratio=1,
            structure="mixed",
        ),
        regime=MarketRegime.RANGING,
    )


def assessment(symbol="BTCUSDT"):
    return StrategyAssessment(
        symbol=symbol,
        strategy="mean_reversion",
        state=StrategyState.WATCH,
        direction=HypothesisDirection.BUY,
        score=81,
        confidence=77.4,
        timeframe="1h+4h",
        entry_low=90,
        entry_high=110,
        stop=95,
        tp1=105,
    )


def point(index, *, symbol="BTCUSDT", rsi=30):
    item = assessment(symbol)
    candidate = MarketCandidate(
        symbol=symbol,
        base_asset=symbol.replace("USDT", ""),
        quote_asset="USDT",
        quote_volume_24h=0,
        price_change_pct_24h=0,
        trade_count_24h=0,
        analyses=(
            analysis("15m", rsi=40, price=99),
            analysis("1h", rsi=rsi, price=98),
            analysis("4h", rsi=45, price=99),
            analysis("1d", rsi=50, price=101),
        ),
    )
    aggregate = AggregatedAssessment(
        symbol=symbol,
        state=StrategyState.WATCH,
        direction=HypothesisDirection.BUY,
        score=item.score,
        confidence=item.confidence,
        supporting_strategies=("mean_reversion",),
    )
    return HistoricalPoint(
        timestamp_ms=(index + 1) * HOUR - 1,
        candidate=candidate,
        assessments=(item,),
        aggregate=aggregate,
    )


def analyzer(*, min_bucket=1):
    return MeanReversionEntryDiagnostics(
        outcome_hours=24,
        min_bucket_observations=min_bucket,
        split_config=TemporalSplitConfig(
            calibration_ratio=0.6,
            validation_ratio=0.2,
            out_of_sample_ratio=0.2,
            min_points_per_segment=2,
        ),
    )


def test_signal_features_use_candidate_state_only():
    item = point(0, rsi=27)
    result = analyzer()._features(
        point=item,
        segment=ValidationSegment.CALIBRATION,
        strategy="mean_reversion",
        net_return_pct=4.0,
        watch_buy_timestamps=(item.timestamp_ms,),
    )
    assert result.rsi_1h == 27
    assert result.ema_distance_pct_1h == pytest.approx(-2.0)
    assert result.net_return_pct == 4.0
    assert result.watch_buy_signals_last_6h == 1


def test_prior_cluster_context_never_counts_future_signal():
    current = point(5)
    stamps = (
        point(4).timestamp_ms,
        current.timestamp_ms,
        point(6).timestamp_ms,
    )
    since, recent = analyzer()._prior_signal_context(
        point=current,
        watch_buy_timestamps=stamps,
    )
    assert since == pytest.approx(1.0)
    assert recent == 2


def test_predefined_buckets_are_deterministic():
    assert _numeric_bucket("rsi_1h", 24) == "<=25"
    assert _numeric_bucket("rsi_1h", 32) == "30-35"
    assert _numeric_bucket("ema_distance_pct_1h", -4) == "<=-3"
    assert _numeric_bucket("watch_buy_signals_last_6h", 5) == "5+"


def test_oos_buckets_are_not_research_eligible():
    item = analyzer()._features(
        point=point(0),
        segment=ValidationSegment.OUT_OF_SAMPLE,
        strategy="mean_reversion",
        net_return_pct=1.0,
        watch_buy_timestamps=(point(0).timestamp_ms,),
    )
    report = analyzer()._segment_report(
        segment=ValidationSegment.OUT_OF_SAMPLE,
        observations=(item,),
    )
    assert report.research_eligible is False
    assert report.buckets
    assert all(row.research_eligible is False for row in report.buckets)


def test_cross_segment_screen_ignores_oos_for_candidate_flags():
    tool = analyzer()
    cal_item = tool._features(
        point=point(0),
        segment=ValidationSegment.CALIBRATION,
        strategy="mean_reversion",
        net_return_pct=2.0,
        watch_buy_timestamps=(point(0).timestamp_ms,),
    )
    val_item = replace(
        cal_item,
        segment=ValidationSegment.VALIDATION.value,
        net_return_pct=3.0,
        positive_return=True,
    )
    oos_item = replace(
        cal_item,
        segment=ValidationSegment.OUT_OF_SAMPLE.value,
        net_return_pct=-20.0,
        positive_return=False,
    )
    segments = (
        tool._segment_report(
            segment=ValidationSegment.CALIBRATION,
            observations=(cal_item,),
        ),
        tool._segment_report(
            segment=ValidationSegment.VALIDATION,
            observations=(val_item,),
        ),
        tool._segment_report(
            segment=ValidationSegment.OUT_OF_SAMPLE,
            observations=(oos_item,),
        ),
    )
    evidence = tool._cross_segment(segments)
    score_bucket = next(
        row for row in evidence if row.feature == "score" and row.bucket == "78-84.99"
    )
    assert score_bucket.stable_positive_return is True


def test_run_symbol_produces_three_chronological_segments():
    points = [point(index) for index in range(12)]
    candles = [candle(index, close=100 + index * 0.1) for index in range(60)]
    tool = analyzer()
    result = tool.run_symbol(
        strategy="mean_reversion",
        points=points,
        candles_by_interval={"1h": candles},
    )
    assert [segment.segment for segment in result.segments] == [
        "calibration",
        "validation",
        "out_of_sample",
    ]
    assert result.strategy == "mean_reversion"
