"""Paper trading performance analytics.

Calculates verifiable metrics from paper fills: expectancy, profit factor,
max drawdown, and other performance indicators.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class PaperTradeRecord:
    """A closed paper trade for performance calculation."""
    symbol: str
    strategy: str
    opened_at: datetime
    closed_at: datetime
    entry_price: float
    exit_price: float
    quantity: float
    pnl_usd: float
    pnl_pct: float
    fees_usd: float
    slippage_usd: float


@dataclass(frozen=True)
class PaperPerformanceMetrics:
    """Calculated performance metrics from paper trades."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    total_pnl_usd: float
    total_fees_usd: float
    total_slippage_usd: float
    net_pnl_usd: float
    profit_factor: float
    expectancy_usd: float
    max_drawdown_usd: float
    max_drawdown_pct: float
    avg_win_usd: float
    avg_loss_usd: float
    avg_trade_usd: float
    by_symbol: dict[str, dict[str, Any]]
    by_strategy: dict[str, dict[str, Any]]


def calculate_paper_metrics(
    trades: list[PaperTradeRecord],
) -> PaperPerformanceMetrics:
    """Calculate performance metrics from a list of closed paper trades.
    
    Args:
        trades: List of closed paper trades with PnL data
        
    Returns:
        PaperPerformanceMetrics with calculated statistics
    """
    if not trades:
        return PaperPerformanceMetrics(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate_pct=0.0,
            total_pnl_usd=0.0,
            total_fees_usd=0.0,
            total_slippage_usd=0.0,
            net_pnl_usd=0.0,
            profit_factor=0.0,
            expectancy_usd=0.0,
            max_drawdown_usd=0.0,
            max_drawdown_pct=0.0,
            avg_win_usd=0.0,
            avg_loss_usd=0.0,
            avg_trade_usd=0.0,
            by_symbol={},
            by_strategy={},
        )

    # Sort by close date for drawdown calculation
    sorted_trades = sorted(trades, key=lambda t: t.closed_at)

    # Basic counts
    total_trades = len(sorted_trades)
    winning_trades = sum(1 for t in sorted_trades if t.pnl_usd > 0)
    losing_trades = sum(1 for t in sorted_trades if t.pnl_usd < 0)
    win_rate_pct = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

    # PnL aggregation
    total_pnl = sum(t.pnl_usd for t in sorted_trades)
    total_fees = sum(t.fees_usd for t in sorted_trades)
    total_slippage = sum(t.slippage_usd for t in sorted_trades)
    net_pnl = total_pnl - total_fees - total_slippage

    # Win/loss averages
    wins = [t.pnl_usd for t in sorted_trades if t.pnl_usd > 0]
    losses = [t.pnl_usd for t in sorted_trades if t.pnl_usd < 0]
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0  # Negative value
    avg_trade = total_pnl / total_trades if total_trades > 0 else 0.0

    # Profit factor = gross profit / gross loss
    gross_profit = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf') if gross_profit > 0 else 0.0

    # Expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
    # Using absolute values for loss_rate * avg_loss
    win_rate = winning_trades / total_trades
    loss_rate = losing_trades / total_trades
    expectancy = (win_rate * avg_win) + (loss_rate * avg_loss)  # avg_loss is already negative

    # Max drawdown (peak-to-trough decline)
    cumulative_pnl = 0.0
    peak_pnl = 0.0
    max_dd_usd = 0.0
    max_dd_pct = 0.0

    for trade in sorted_trades:
        cumulative_pnl += trade.pnl_usd
        if cumulative_pnl > peak_pnl:
            peak_pnl = cumulative_pnl
        drawdown = peak_pnl - cumulative_pnl
        if drawdown > max_dd_usd:
            max_dd_usd = drawdown
            # Calculate drawdown percentage from peak
            if peak_pnl > 0:
                max_dd_pct = (drawdown / peak_pnl) * 100

    # By symbol aggregation
    by_symbol: dict[str, dict[str, Any]] = {}
    for trade in sorted_trades:
        sym = trade.symbol
        if sym not in by_symbol:
            by_symbol[sym] = {"trades": 0, "wins": 0, "pnl_usd": 0.0, "fees_usd": 0.0}
        by_symbol[sym]["trades"] += 1
        by_symbol[sym]["pnl_usd"] += trade.pnl_usd
        by_symbol[sym]["fees_usd"] += trade.fees_usd
        if trade.pnl_usd > 0:
            by_symbol[sym]["wins"] += 1

    # By strategy aggregation
    by_strategy: dict[str, dict[str, Any]] = {}
    for trade in sorted_trades:
        strat = trade.strategy
        if strat not in by_strategy:
            by_strategy[strat] = {"trades": 0, "wins": 0, "pnl_usd": 0.0, "fees_usd": 0.0}
        by_strategy[strat]["trades"] += 1
        by_strategy[strat]["pnl_usd"] += trade.pnl_usd
        by_strategy[strat]["fees_usd"] += trade.fees_usd
        if trade.pnl_usd > 0:
            by_strategy[strat]["wins"] += 1

    return PaperPerformanceMetrics(
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate_pct=round(win_rate_pct, 2),
        total_pnl_usd=round(total_pnl, 2),
        total_fees_usd=round(total_fees, 2),
        total_slippage_usd=round(total_slippage, 2),
        net_pnl_usd=round(net_pnl, 2),
        profit_factor=round(profit_factor, 2) if profit_factor != float('inf') else float('inf'),
        expectancy_usd=round(expectancy, 2),
        max_drawdown_usd=round(max_dd_usd, 2),
        max_drawdown_pct=round(max_dd_pct, 2),
        avg_win_usd=round(avg_win, 2),
        avg_loss_usd=round(avg_loss, 2),
        avg_trade_usd=round(avg_trade, 2),
        by_symbol=by_symbol,
        by_strategy=by_strategy,
    )
