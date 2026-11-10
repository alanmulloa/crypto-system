from dataclasses import replace

import pytest

from app.evaluation import (
    BacktestConfig,
    BacktestExitReason,
    BacktestSimulator,
    HistoricalPoint,
)
from app.market.types import Candle, IndicatorSnapshot, MarketCandidate, MarketRegime, TimeframeAnalysis
from app.strategies import (
    AggregatedAssessment,
    HypothesisDirection,
    StrategyAssessment,
    StrategyState,
)


HOUR = 60 * 60 * 1000


def candle(index, *, open_price, high, low, close):
    return Candle(
        open_time_ms=index * HOUR,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=1000,
        close_time_ms=(index + 1) * HOUR - 1,
    )


def candidate(price=100):
    analysis = TimeframeAnalysis(
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
        regime=MarketRegime.BULLISH,
    )
    h4 = replace(analysis, interval="4h")
    return MarketCandidate(
        symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
        quote_volume_24h=1_000_000,
        price_change_pct_24h=1,
        trade_count_24h=10_000,
        analyses=(analysis, h4),
    )


def assessment(
    *,
    state=StrategyState.WATCH,
    direction=HypothesisDirection.BUY,
    entry_low=99,
    entry_high=101,
    stop=95,
    tp1=110,
):
    return StrategyAssessment(
        symbol="BTCUSDT",
        strategy="trend_following",
        state=state,
        direction=direction,
        score=80 if state is not StrategyState.REJECT else 0,
        confidence=75 if state is not StrategyState.REJECT else 0,
        timeframe="1h+4h",
        entry_low=entry_low,
        entry_high=entry_high,
        stop=stop,
        tp1=tp1,
    )


def point(signal_index=0, item=None):
    item = item or assessment()
    aggregate = AggregatedAssessment(
        symbol="BTCUSDT",
        state=item.state,
        direction=item.direction,
        score=item.score,
        confidence=item.confidence,
        supporting_strategies=(item.strategy,) if item.direction else (),
    )
    return HistoricalPoint(
        timestamp_ms=(signal_index + 1) * HOUR - 1,
        candidate=candidate(),
        assessments=(item,),
        aggregate=aggregate,
    )


def test_entry_uses_first_candle_strictly_after_signal():
    candles = [
        candle(0, open_price=100, high=101, low=99, close=100),
        candle(1, open_price=100, high=104, low=99, close=103),
        candle(2, open_price=103, high=111, low=102, close=110),
    ]
    simulator = BacktestSimulator(
        BacktestConfig(
            fee_bps=0,
            slippage_bps=0,
            max_holding_ms=2 * HOUR,
        )
    )
    report = simulator.run_strategy(
        strategy="trend_following",
        points=[point(signal_index=0)],
        candles_by_interval={"1h": candles},
    )
    assert report.trade_count == 1
    assert report.trades[0].entry_timestamp_ms == candles[1].open_time_ms


def test_stop_wins_if_stop_and_tp_are_both_touched_same_candle():
    candles = [
        candle(0, open_price=100, high=101, low=99, close=100),
        candle(1, open_price=100, high=112, low=94, close=105),
    ]
    simulator = BacktestSimulator(
        BacktestConfig(fee_bps=0, slippage_bps=0, max_holding_ms=HOUR)
    )
    report = simulator.run_strategy(
        strategy="trend_following",
        points=[point()],
        candles_by_interval={"1h": candles},
    )
    assert report.trade_count == 1
    assert report.trades[0].exit_reason is BacktestExitReason.STOP
    assert report.trades[0].exit_price == 95


def test_fees_and_slippage_reduce_profit():
    candles = [
        candle(0, open_price=100, high=101, low=99, close=100),
        candle(1, open_price=100, high=111, low=99, close=110),
    ]
    clean = BacktestSimulator(
        BacktestConfig(fee_bps=0, slippage_bps=0, max_holding_ms=HOUR)
    ).run_strategy(
        strategy="trend_following",
        points=[point()],
        candles_by_interval={"1h": candles},
    )
    costly = BacktestSimulator(
        BacktestConfig(fee_bps=10, slippage_bps=50, max_holding_ms=HOUR)
    ).run_strategy(
        strategy="trend_following",
        points=[point()],
        candles_by_interval={"1h": candles},
    )
    assert clean.trades[0].pnl_usd > costly.trades[0].pnl_usd


def test_sell_hypothesis_is_skipped_in_spot_only_mode():
    sell = assessment(
        direction=HypothesisDirection.SELL,
        entry_low=99,
        entry_high=101,
        stop=105,
        tp1=90,
    )
    candles = [
        candle(0, open_price=100, high=101, low=99, close=100),
        candle(1, open_price=100, high=101, low=89, close=90),
    ]
    report = BacktestSimulator(
        BacktestConfig(fee_bps=0, slippage_bps=0)
    ).run_strategy(
        strategy="trend_following",
        points=[point(item=sell)],
        candles_by_interval={"1h": candles},
    )
    assert report.trade_count == 0
    assert report.skipped_sell == 1


def test_entry_outside_strategy_range_is_skipped():
    candles = [
        candle(0, open_price=100, high=101, low=99, close=100),
        candle(1, open_price=104, high=110, low=103, close=109),
    ]
    report = BacktestSimulator(
        BacktestConfig(fee_bps=0, slippage_bps=0)
    ).run_strategy(
        strategy="trend_following",
        points=[point()],
        candles_by_interval={"1h": candles},
    )
    assert report.trade_count == 0
    assert report.skipped_no_entry == 1


def test_overlapping_signal_is_skipped_until_prior_trade_closes():
    candles = [
        candle(0, open_price=100, high=101, low=99, close=100),
        candle(1, open_price=100, high=104, low=99, close=103),
        candle(2, open_price=100, high=104, low=99, close=103),
        candle(3, open_price=103, high=104, low=102, close=103),
        candle(4, open_price=103, high=104, low=102, close=103),
    ]
    simulator = BacktestSimulator(
        BacktestConfig(
            fee_bps=0,
            slippage_bps=0,
            max_holding_ms=3 * HOUR,
            require_entry_range=False,
        )
    )
    report = simulator.run_strategy(
        strategy="trend_following",
        points=[point(signal_index=0), point(signal_index=1)],
        candles_by_interval={"1h": candles},
    )
    assert report.trade_count == 1
    assert report.skipped_overlap == 1


def test_report_metrics_include_expectancy_profit_factor_and_drawdown():
    candles = [
        candle(0, open_price=100, high=101, low=99, close=100),
        candle(1, open_price=100, high=111, low=99, close=110),
        candle(2, open_price=100, high=101, low=94, close=95),
        candle(3, open_price=100, high=111, low=99, close=110),
    ]
    points = [
        point(signal_index=0),
        point(signal_index=1),
        point(signal_index=2),
    ]
    simulator = BacktestSimulator(
        BacktestConfig(
            initial_cash_usd=1000,
            notional_usd=100,
            fee_bps=0,
            slippage_bps=0,
            max_holding_ms=HOUR,
            require_entry_range=False,
        )
    )
    report = simulator.run_strategy(
        strategy="trend_following",
        points=points,
        candles_by_interval={"1h": candles},
    )
    assert report.trade_count >= 1
    assert report.expectancy_usd is not None
    assert report.win_rate_pct is not None
    assert report.max_closed_equity_drawdown_pct >= 0
    if report.gross_loss_usd > 0:
        assert report.profit_factor is not None


def test_run_all_strategies_returns_independent_reports():
    candles = [
        candle(0, open_price=100, high=101, low=99, close=100),
        candle(1, open_price=100, high=111, low=99, close=110),
    ]
    first = assessment()
    second = replace(first, strategy="momentum")
    aggregate = AggregatedAssessment(
        symbol="BTCUSDT",
        state=StrategyState.WATCH,
        direction=HypothesisDirection.BUY,
        score=80,
        confidence=75,
        supporting_strategies=("trend_following", "momentum"),
    )
    hp = HistoricalPoint(
        timestamp_ms=HOUR - 1,
        candidate=candidate(),
        assessments=(first, second),
        aggregate=aggregate,
    )
    reports = BacktestSimulator(
        BacktestConfig(fee_bps=0, slippage_bps=0, max_holding_ms=HOUR)
    ).run_all_strategies(
        points=[hp],
        candles_by_interval={"1h": candles},
    )
    assert {report.strategy for report in reports} == {"momentum", "trend_following"}
