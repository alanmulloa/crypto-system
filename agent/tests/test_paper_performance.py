from datetime import datetime, timezone, timedelta

import pytest

from app.evaluation.paper_performance import (
    PaperTradeRecord,
    calculate_paper_metrics,
)


NOW = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)


def make_trade(
    symbol="BTCUSDT",
    strategy="MOMENTUM",
    pnl_usd=100.0,
    pnl_pct=5.0,
    fees_usd=1.0,
    slippage_usd=0.5,
    opened_days_ago=1,
    closed_days_ago=0,
):
    return PaperTradeRecord(
        symbol=symbol,
        strategy=strategy,
        opened_at=NOW - timedelta(days=opened_days_ago),
        closed_at=NOW - timedelta(days=closed_days_ago),
        entry_price=100.0,
        exit_price=100.0 + (pnl_pct * 2),
        quantity=1.0,
        pnl_usd=pnl_usd,
        pnl_pct=pnl_pct,
        fees_usd=fees_usd,
        slippage_usd=slippage_usd,
    )


def test_empty_trades_return_zero_metrics():
    metrics = calculate_paper_metrics([])
    assert metrics.total_trades == 0
    assert metrics.win_rate_pct == 0.0
    assert metrics.total_pnl_usd == 0.0
    assert metrics.profit_factor == 0.0
    assert metrics.expectancy_usd == 0.0
    assert metrics.max_drawdown_usd == 0.0


def test_all_winning_trades():
    trades = [
        make_trade(pnl_usd=100.0, opened_days_ago=2),
        make_trade(pnl_usd=50.0, opened_days_ago=1),
        make_trade(pnl_usd=200.0, opened_days_ago=3),
    ]
    metrics = calculate_paper_metrics(trades)
    assert metrics.total_trades == 3
    assert metrics.winning_trades == 3
    assert metrics.losing_trades == 0
    assert metrics.win_rate_pct == 100.0
    assert metrics.total_pnl_usd == 350.0
    assert metrics.avg_win_usd == pytest.approx(116.67, rel=0.01)
    assert metrics.profit_factor == float('inf')  # No losses
    assert metrics.max_drawdown_usd == 0.0


def test_all_losing_trades():
    trades = [
        make_trade(pnl_usd=-100.0, opened_days_ago=2),
        make_trade(pnl_usd=-50.0, opened_days_ago=1),
        make_trade(pnl_usd=-200.0, opened_days_ago=3),
    ]
    metrics = calculate_paper_metrics(trades)
    assert metrics.total_trades == 3
    assert metrics.winning_trades == 0
    assert metrics.losing_trades == 3
    assert metrics.win_rate_pct == 0.0
    assert metrics.total_pnl_usd == -350.0
    assert metrics.avg_loss_usd == pytest.approx(-116.67, rel=0.01)
    assert metrics.profit_factor == 0.0
    assert metrics.max_drawdown_usd > 0


def test_mixed_trades():
    trades = [
        make_trade(pnl_usd=100.0, opened_days_ago=4, closed_days_ago=4),
        make_trade(pnl_usd=-50.0, opened_days_ago=3, closed_days_ago=3),
        make_trade(pnl_usd=200.0, opened_days_ago=2, closed_days_ago=2),
        make_trade(pnl_usd=-100.0, opened_days_ago=1, closed_days_ago=1),
        make_trade(pnl_usd=50.0, opened_days_ago=5, closed_days_ago=5),
    ]
    metrics = calculate_paper_metrics(trades)
    
    # Sorted by close date: 5d ago(50), 4d ago(100), 3d ago(-50), 2d ago(200), 1d ago(-100)
    assert metrics.total_trades == 5
    assert metrics.winning_trades == 3
    assert metrics.losing_trades == 2
    assert metrics.win_rate_pct == 60.0
    
    # Total: 50+100-50+200-100 = 200
    assert metrics.total_pnl_usd == 200.0
    
    # Win rate = 60%, avg win = (50+100+200)/3 = 116.67
    assert metrics.avg_win_usd == pytest.approx(116.67, rel=0.01)
    
    # Loss rate = 40%, avg loss = (-50-100)/2 = -75
    assert metrics.avg_loss_usd == pytest.approx(-75.0, rel=0.01)
    
    # Profit factor = (50+100+200) / (50+100) = 350/150 = 2.33
    assert metrics.profit_factor == pytest.approx(2.33, rel=0.01)
    
    # Expectancy = 0.6 * 116.67 + 0.4 * (-75) = 70 - 30 = 40
    assert metrics.expectancy_usd == pytest.approx(40.0, rel=0.01)
    
    # Max drawdown: cumulative = 50, 150, 100, 300, 200
    # Peak = 150, trough = 100 -> DD = 50
    # Peak = 300, trough = 200 -> DD = 100 (this is the max)
    assert metrics.max_drawdown_usd == 100.0


def test_fees_and_slippage_included():
    trades = [
        make_trade(
            pnl_usd=100.0,
            fees_usd=2.0,
            slippage_usd=1.0,
            opened_days_ago=2,
        ),
        make_trade(
            pnl_usd=-50.0,
            fees_usd=1.0,
            slippage_usd=0.5,
            opened_days_ago=1,
        ),
    ]
    metrics = calculate_paper_metrics(trades)
    
    assert metrics.total_fees_usd == 3.0
    assert metrics.total_slippage_usd == 1.5
    assert metrics.net_pnl_usd == 100.0 - 50.0 - 3.0 - 1.5  # 45.5


def test_by_symbol_aggregation():
    trades = [
        make_trade(symbol="BTCUSDT", strategy="MOMENTUM", pnl_usd=100.0, opened_days_ago=2),
        make_trade(symbol="BTCUSDT", strategy="MOMENTUM", pnl_usd=-50.0, opened_days_ago=1),
        make_trade(symbol="ETHUSDT", strategy="TREND", pnl_usd=200.0, opened_days_ago=3),
    ]
    metrics = calculate_paper_metrics(trades)
    
    assert "BTCUSDT" in metrics.by_symbol
    assert metrics.by_symbol["BTCUSDT"]["trades"] == 2
    assert metrics.by_symbol["BTCUSDT"]["wins"] == 1
    assert metrics.by_symbol["BTCUSDT"]["pnl_usd"] == 50.0
    
    assert "ETHUSDT" in metrics.by_symbol
    assert metrics.by_symbol["ETHUSDT"]["trades"] == 1
    assert metrics.by_symbol["ETHUSDT"]["wins"] == 1
    assert metrics.by_symbol["ETHUSDT"]["pnl_usd"] == 200.0


def test_by_strategy_aggregation():
    trades = [
        make_trade(symbol="BTCUSDT", strategy="MOMENTUM", pnl_usd=100.0, opened_days_ago=2),
        make_trade(symbol="ETHUSDT", strategy="MOMENTUM", pnl_usd=50.0, opened_days_ago=1),
        make_trade(symbol="BTCUSDT", strategy="TREND", pnl_usd=-30.0, opened_days_ago=3),
    ]
    metrics = calculate_paper_metrics(trades)
    
    assert "MOMENTUM" in metrics.by_strategy
    assert metrics.by_strategy["MOMENTUM"]["trades"] == 2
    assert metrics.by_strategy["MOMENTUM"]["wins"] == 2
    assert metrics.by_strategy["MOMOMENTUM"]["pnl_usd"] if "MOMOMENTUM" in metrics.by_strategy else True
    assert metrics.by_strategy["MOMENTUM"]["pnl_usd"] == 150.0
    
    assert "TREND" in metrics.by_strategy
    assert metrics.by_strategy["TREND"]["trades"] == 1
    assert metrics.by_strategy["TREND"]["wins"] == 0
    assert metrics.by_strategy["TREND"]["pnl_usd"] == -30.0


def test_drawdown_calculation():
    # Create a sequence that has a clear drawdown
    trades = [
        make_trade(pnl_usd=100.0, opened_days_ago=5, closed_days_ago=5),  # Peak at 100
        make_trade(pnl_usd=50.0, opened_days_ago=4, closed_days_ago=4),   # Peak at 150
        make_trade(pnl_usd=-30.0, opened_days_ago=3, closed_days_ago=3),  # Down to 120
        make_trade(pnl_usd=-80.0, opened_days_ago=2, closed_days_ago=2),  # Down to 40 (DD = 110)
        make_trade(pnl_usd=60.0, opened_days_ago=1, closed_days_ago=1),   # Up to 100
    ]
    metrics = calculate_paper_metrics(trades)
    
    # Max drawdown = peak(150) - trough(40) = 110
    assert metrics.max_drawdown_usd == 110.0


def test_drawdown_percentage():
    # Need to have wins first, then losses for drawdown to make sense
    trades = [
        make_trade(pnl_usd=100.0, opened_days_ago=3, closed_days_ago=3),  # First win
        make_trade(pnl_usd=50.0, opened_days_ago=2, closed_days_ago=2),   # Second win, peak at 150
        make_trade(pnl_usd=-40.0, opened_days_ago=1, closed_days_ago=1),  # Loss, down to 110, DD = 40/150 = 26.67%
    ]
    metrics = calculate_paper_metrics(trades)
    
    # Cumulative: 100, 150, 110
    # Peak = 150, trough = 110 -> DD = 40
    # DD % = 40/150 * 100 = 26.67%
    assert metrics.max_drawdown_usd == 40.0
    assert metrics.max_drawdown_pct == pytest.approx(26.67, rel=0.01)


def test_profit_factor_with_no_losses():
    trades = [
        make_trade(pnl_usd=100.0, opened_days_ago=2),
        make_trade(pnl_usd=50.0, opened_days_ago=1),
    ]
    metrics = calculate_paper_metrics(trades)
    assert metrics.profit_factor == float('inf')


def test_profit_factor_with_no_wins():
    trades = [
        make_trade(pnl_usd=-100.0, opened_days_ago=2),
        make_trade(pnl_usd=-50.0, opened_days_ago=1),
    ]
    metrics = calculate_paper_metrics(trades)
    assert metrics.profit_factor == 0.0
