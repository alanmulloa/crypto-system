from dataclasses import replace

import pytest

from app.evaluation import (
    BacktestConfig,
    BacktestSimulator,
    HistoricalPoint,
    OutcomeEvaluator,
    TemporalSplitConfig,
    TemporalValidator,
    ValidationSegment,
    regime_performance,
    score_threshold_sensitivity,
)
from app.market.types import Candle, IndicatorSnapshot, MarketCandidate, MarketRegime, TimeframeAnalysis
from app.strategies import (
    AggregatedAssessment,
    HypothesisDirection,
    StrategyAssessment,
    StrategyState,
)


HOUR = 60 * 60 * 1000


def candle(index, price=100.0):
    return Candle(
        open_time_ms=index * HOUR,
        open=price,
        high=price + 2,
        low=max(1.0, price - 2),
        close=price + 0.5,
        volume=1000,
        close_time_ms=(index + 1) * HOUR - 1,
    )


def candidate(price=100.0, regime=MarketRegime.BULLISH):
    one_hour = TimeframeAnalysis(
        interval="1h",
        candles=100,
        last_price=price,
        indicators=IndicatorSnapshot(
            ema_fast=101,
            ema_slow=99,
            rsi=60,
            atr=2,
            atr_pct=2,
            volume_ratio=1.5,
            structure="higher_highs_higher_lows",
        ),
        regime=regime,
    )
    four_hour = replace(one_hour, interval="4h")
    return MarketCandidate(
        symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
        quote_volume_24h=1_000_000,
        price_change_pct_24h=1,
        trade_count_24h=10_000,
        analyses=(one_hour, four_hour),
    )


def point(index, *, score=80, state=StrategyState.WATCH, regime=MarketRegime.BULLISH):
    assessment = StrategyAssessment(
        symbol="BTCUSDT",
        strategy="trend_following",
        state=state,
        direction=(
            HypothesisDirection.BUY
            if state is not StrategyState.REJECT
            else None
        ),
        score=score if state is not StrategyState.REJECT else 0,
        confidence=75 if state is not StrategyState.REJECT else 0,
        timeframe="1h+4h",
        entry_low=95 if state is not StrategyState.REJECT else None,
        entry_high=105 if state is not StrategyState.REJECT else None,
        stop=90 if state is not StrategyState.REJECT else None,
        tp1=110 if state is not StrategyState.REJECT else None,
    )
    aggregate = AggregatedAssessment(
        symbol="BTCUSDT",
        state=state,
        direction=assessment.direction,
        score=assessment.score,
        confidence=assessment.confidence,
        supporting_strategies=("trend_following",) if assessment.direction else (),
    )
    return HistoricalPoint(
        timestamp_ms=(index + 1) * HOUR - 1,
        candidate=candidate(regime=regime),
        assessments=(assessment,),
        aggregate=aggregate,
    )


def points(count=30):
    return tuple(
        point(
            index,
            score=70 + (index % 4) * 5,
            state=(
                StrategyState.REJECT
                if index % 7 == 0
                else StrategyState.WATCH
            ),
            regime=(
                MarketRegime.RANGING
                if index % 5 == 0
                else MarketRegime.BULLISH
            ),
        )
        for index in range(count)
    )


def candles(count=40):
    return tuple(candle(index, 100 + index * 0.2) for index in range(count))


def validator():
    return TemporalValidator(
        backtest_simulator=BacktestSimulator(
            BacktestConfig(
                initial_cash_usd=1000,
                notional_usd=100,
                fee_bps=0,
                slippage_bps=0,
                max_holding_ms=2 * HOUR,
                require_entry_range=False,
            )
        ),
        outcome_evaluator=OutcomeEvaluator(
            horizons_ms={"24h": 2 * HOUR}
        ),
        split_config=TemporalSplitConfig(
            calibration_ratio=0.6,
            validation_ratio=0.2,
            out_of_sample_ratio=0.2,
            min_points_per_segment=3,
        ),
        outcome_horizon="24h",
    )


def test_split_is_chronological_and_non_overlapping():
    split = validator().split_points(points(30))
    calibration = split[ValidationSegment.CALIBRATION]
    validation = split[ValidationSegment.VALIDATION]
    oos = split[ValidationSegment.OUT_OF_SAMPLE]

    assert len(calibration) == 18
    assert len(validation) == 6
    assert len(oos) == 6
    assert calibration[-1].timestamp_ms < validation[0].timestamp_ms
    assert validation[-1].timestamp_ms < oos[0].timestamp_ms


def test_split_rejects_insufficient_history():
    with pytest.raises(ValueError):
        validator().split_points(points(8))


def test_candle_bounding_removes_future_segment_data():
    bounded = validator()._candles_until(
        {"1h": candles(20)},
        end_timestamp_ms=10 * HOUR - 1,
    )
    assert bounded["1h"]
    assert max(item.close_time_ms for item in bounded["1h"]) <= 10 * HOUR - 1


def test_validation_returns_all_three_segments():
    report = validator().validate_strategy(
        strategy="trend_following",
        points=points(30),
        candles_by_interval={"1h": candles(40)},
    )
    assert report.calibration.segment is ValidationSegment.CALIBRATION
    assert report.validation.segment is ValidationSegment.VALIDATION
    assert report.out_of_sample.segment is ValidationSegment.OUT_OF_SAMPLE
    assert report.strategy == "trend_following"


def test_segment_end_prevents_trade_from_using_next_segment_future():
    small = validator()
    split = small.split_points(points(30))
    calibration_points = split[ValidationSegment.CALIBRATION]
    end = calibration_points[-1].timestamp_ms

    bounded = small._candles_until(
        {"1h": candles(40)},
        end_timestamp_ms=end,
    )
    assert all(item.close_time_ms <= end for item in bounded["1h"])


def test_score_sensitivity_counts_never_increase_with_higher_threshold():
    observations = OutcomeEvaluator(
        horizons_ms={"24h": 2 * HOUR}
    ).evaluate_points(
        points=points(20),
        candles_by_interval={"1h": candles(30)},
    )
    sensitivity = score_threshold_sensitivity(
        observations,
        strategy="trend_following",
        horizon="24h",
        thresholds=(70, 75, 80, 85),
    )
    counts = [item.observations for item in sensitivity]
    assert counts == sorted(counts, reverse=True)


def test_regime_performance_partitions_backtest_trades():
    report = BacktestSimulator(
        BacktestConfig(
            fee_bps=0,
            slippage_bps=0,
            max_holding_ms=HOUR,
            require_entry_range=False,
        )
    ).run_strategy(
        strategy="trend_following",
        points=points(10),
        candles_by_interval={"1h": candles(20)},
    )
    regimes = regime_performance(report)
    assert sum(item.trades for item in regimes) == report.trade_count


def test_rejected_outcomes_are_reported_separately():
    report = validator().validate_strategy(
        strategy="trend_following",
        points=points(30),
        candles_by_interval={"1h": candles(40)},
    )
    assert report.calibration.rejected_outcome.observations >= 0
    assert report.calibration.watch_outcome.observations >= 0


def test_validation_is_deterministic():
    kwargs = dict(
        strategy="trend_following",
        points=points(30),
        candles_by_interval={"1h": candles(40)},
    )
    first = validator().validate_strategy(**kwargs)
    second = validator().validate_strategy(**kwargs)
    assert first == second
