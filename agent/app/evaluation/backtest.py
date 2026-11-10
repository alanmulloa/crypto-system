from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import inf
from typing import Mapping, Sequence

from app.evaluation.historical import HistoricalPoint
from app.market.types import Candle
from app.strategies.base import HypothesisDirection, StrategyAssessment, StrategyState


class BacktestExitReason(str, Enum):
    STOP = "STOP"
    TP1 = "TP1"
    HORIZON = "HORIZON"


@dataclass(frozen=True)
class BacktestConfig:
    initial_cash_usd: float = 10_000.0
    notional_usd: float = 100.0
    fee_bps: float = 10.0
    slippage_bps: float = 5.0
    max_holding_ms: int = 24 * 60 * 60 * 1000
    outcome_interval: str = "1h"
    require_entry_range: bool = True

    def __post_init__(self) -> None:
        if self.initial_cash_usd <= 0:
            raise ValueError("initial_cash_usd must be positive")
        if self.notional_usd <= 0:
            raise ValueError("notional_usd must be positive")
        if self.fee_bps < 0 or self.slippage_bps < 0:
            raise ValueError("fee/slippage cannot be negative")
        if self.max_holding_ms <= 0:
            raise ValueError("max_holding_ms must be positive")


@dataclass(frozen=True)
class BacktestTrade:
    symbol: str
    strategy: str
    direction: HypothesisDirection
    signal_timestamp_ms: int
    entry_timestamp_ms: int
    exit_timestamp_ms: int
    entry_price: float
    exit_price: float
    quantity: float
    entry_notional_usd: float
    entry_fee_usd: float
    exit_fee_usd: float
    pnl_usd: float
    return_pct: float
    mfe_pct: float
    mae_pct: float
    exit_reason: BacktestExitReason
    market_regime: str | None


@dataclass(frozen=True)
class BacktestReport:
    strategy: str
    initial_cash_usd: float
    ending_cash_usd: float
    trades: tuple[BacktestTrade, ...]
    skipped_non_watch: int
    skipped_sell: int
    skipped_no_entry: int
    skipped_overlap: int
    skipped_no_exit: int
    gross_profit_usd: float
    gross_loss_usd: float
    net_pnl_usd: float
    expectancy_usd: float | None
    profit_factor: float | None
    win_rate_pct: float | None
    max_closed_equity_drawdown_pct: float

    @property
    def trade_count(self) -> int:
        return len(self.trades)


class BacktestSimulator:
    """Deterministic spot-only strategy backtester.

    The simulator evaluates one strategy independently. SELL hypotheses are
    always skipped because this project does not simulate shorts or Margin.
    """

    def __init__(self, config: BacktestConfig | None = None):
        self.config = config or BacktestConfig()

    @staticmethod
    def _regime(point: HistoricalPoint) -> str | None:
        analysis = point.candidate.analysis_for("4h") or point.candidate.analysis_for("1h")
        return analysis.regime.value if analysis else None

    def _entry_execution_price(self, market_price: float) -> float:
        return market_price * (1.0 + self.config.slippage_bps / 10_000.0)

    def _exit_execution_price(self, market_price: float) -> float:
        return market_price * (1.0 - self.config.slippage_bps / 10_000.0)

    @staticmethod
    def _assessment_for(point: HistoricalPoint, strategy: str) -> StrategyAssessment | None:
        return next(
            (
                assessment
                for assessment in point.assessments
                if assessment.strategy == strategy
            ),
            None,
        )

    def _entry_candle(
        self,
        *,
        point: HistoricalPoint,
        assessment: StrategyAssessment,
        candles: Sequence[Candle],
    ) -> Candle | None:
        candle = next(
            (
                item
                for item in candles
                if item.open_time_ms > point.timestamp_ms
            ),
            None,
        )
        if candle is None:
            return None

        if self.config.require_entry_range:
            if assessment.entry_low is None or assessment.entry_high is None:
                return None
            if not assessment.entry_low <= candle.open <= assessment.entry_high:
                return None

        return candle

    def _simulate_trade(
        self,
        *,
        point: HistoricalPoint,
        assessment: StrategyAssessment,
        candles: Sequence[Candle],
        available_cash: float,
    ) -> BacktestTrade | None:
        entry_candle = self._entry_candle(
            point=point,
            assessment=assessment,
            candles=candles,
        )
        if entry_candle is None:
            return None

        fee_rate = self.config.fee_bps / 10_000.0
        max_notional = available_cash / (1.0 + fee_rate)
        entry_notional = min(self.config.notional_usd, max_notional)
        if entry_notional <= 0:
            return None

        entry_price = self._entry_execution_price(entry_candle.open)
        quantity = entry_notional / entry_price
        entry_fee = entry_notional * fee_rate
        exit_target_ms = entry_candle.open_time_ms + self.config.max_holding_ms

        stop = assessment.stop
        tp1 = assessment.tp1
        path: list[Candle] = []
        exit_reason: BacktestExitReason | None = None
        exit_market_price: float | None = None
        exit_timestamp_ms: int | None = None

        for candle in candles:
            if candle.open_time_ms < entry_candle.open_time_ms:
                continue
            if candle.close_time_ms <= point.timestamp_ms:
                continue

            path.append(candle)

            if assessment.direction is HypothesisDirection.BUY:
                stop_hit = stop is not None and candle.low <= stop
                tp_hit = tp1 is not None and candle.high >= tp1
            else:
                stop_hit = stop is not None and candle.high >= stop
                tp_hit = tp1 is not None and candle.low <= tp1

            # Conservative intrabar ambiguity rule: stop first.
            if stop_hit:
                exit_reason = BacktestExitReason.STOP
                exit_market_price = float(stop)
                exit_timestamp_ms = candle.close_time_ms
                break
            if tp_hit:
                exit_reason = BacktestExitReason.TP1
                exit_market_price = float(tp1)
                exit_timestamp_ms = candle.close_time_ms
                break
            if candle.close_time_ms >= exit_target_ms:
                exit_reason = BacktestExitReason.HORIZON
                exit_market_price = candle.close
                exit_timestamp_ms = candle.close_time_ms
                break

        if (
            not path
            or exit_reason is None
            or exit_market_price is None
            or exit_timestamp_ms is None
        ):
            return None

        exit_price = self._exit_execution_price(exit_market_price)
        exit_gross = quantity * exit_price
        exit_fee = exit_gross * fee_rate
        net_exit = exit_gross - exit_fee
        total_entry_cost = entry_notional + entry_fee
        pnl = net_exit - total_entry_cost
        return_pct = pnl / total_entry_cost * 100.0 if total_entry_cost else 0.0

        max_high = max(candle.high for candle in path)
        min_low = min(candle.low for candle in path)
        max_up = (max_high / entry_price - 1.0) * 100.0
        max_down = (min_low / entry_price - 1.0) * 100.0

        if assessment.direction is HypothesisDirection.BUY:
            mfe = max(max_up, 0.0)
            mae = max(-max_down, 0.0)
        else:
            mfe = max(-max_down, 0.0)
            mae = max(max_up, 0.0)

        return BacktestTrade(
            symbol=assessment.symbol,
            strategy=assessment.strategy,
            direction=assessment.direction,
            signal_timestamp_ms=point.timestamp_ms,
            entry_timestamp_ms=entry_candle.open_time_ms,
            exit_timestamp_ms=exit_timestamp_ms,
            entry_price=entry_price,
            exit_price=exit_price,
            quantity=quantity,
            entry_notional_usd=entry_notional,
            entry_fee_usd=entry_fee,
            exit_fee_usd=exit_fee,
            pnl_usd=pnl,
            return_pct=return_pct,
            mfe_pct=mfe,
            mae_pct=mae,
            exit_reason=exit_reason,
            market_regime=self._regime(point),
        )

    @staticmethod
    def _max_closed_equity_drawdown(equity_points: Sequence[float]) -> float:
        if not equity_points:
            return 0.0
        peak = equity_points[0]
        max_dd = 0.0
        for value in equity_points:
            peak = max(peak, value)
            if peak <= 0:
                continue
            drawdown = (peak - value) / peak * 100.0
            max_dd = max(max_dd, drawdown)
        return max_dd

    def run_strategy(
        self,
        *,
        strategy: str,
        points: Sequence[HistoricalPoint],
        candles_by_interval: Mapping[str, Sequence[Candle]],
    ) -> BacktestReport:
        candles = candles_by_interval.get(self.config.outcome_interval)
        if not candles:
            raise ValueError(f"missing outcome interval {self.config.outcome_interval}")

        cash = self.config.initial_cash_usd
        equity_points = [cash]
        trades: list[BacktestTrade] = []
        active_until_ms = -inf

        skipped_non_watch = 0
        skipped_sell = 0
        skipped_no_entry = 0
        skipped_overlap = 0
        skipped_no_exit = 0

        for point in sorted(points, key=lambda item: item.timestamp_ms):
            assessment = self._assessment_for(point, strategy)
            if assessment is None:
                continue
            if assessment.state is not StrategyState.WATCH or assessment.direction is None:
                skipped_non_watch += 1
                continue
            if assessment.direction is HypothesisDirection.SELL:
                skipped_sell += 1
                continue
            if point.timestamp_ms < active_until_ms:
                skipped_overlap += 1
                continue

            entry_candle = self._entry_candle(
                point=point,
                assessment=assessment,
                candles=candles,
            )
            if entry_candle is None:
                skipped_no_entry += 1
                continue

            trade = self._simulate_trade(
                point=point,
                assessment=assessment,
                candles=candles,
                available_cash=cash,
            )
            if trade is None:
                skipped_no_exit += 1
                continue

            cash += trade.pnl_usd
            active_until_ms = trade.exit_timestamp_ms
            trades.append(trade)
            equity_points.append(cash)

        wins = [trade.pnl_usd for trade in trades if trade.pnl_usd > 0]
        losses = [trade.pnl_usd for trade in trades if trade.pnl_usd < 0]
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        net_pnl = sum(trade.pnl_usd for trade in trades)

        expectancy = net_pnl / len(trades) if trades else None
        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        elif gross_profit > 0:
            profit_factor = inf
        else:
            profit_factor = None

        win_rate = (
            len(wins) / len(trades) * 100.0
            if trades
            else None
        )

        return BacktestReport(
            strategy=strategy,
            initial_cash_usd=self.config.initial_cash_usd,
            ending_cash_usd=cash,
            trades=tuple(trades),
            skipped_non_watch=skipped_non_watch,
            skipped_sell=skipped_sell,
            skipped_no_entry=skipped_no_entry,
            skipped_overlap=skipped_overlap,
            skipped_no_exit=skipped_no_exit,
            gross_profit_usd=gross_profit,
            gross_loss_usd=gross_loss,
            net_pnl_usd=net_pnl,
            expectancy_usd=expectancy,
            profit_factor=profit_factor,
            win_rate_pct=win_rate,
            max_closed_equity_drawdown_pct=self._max_closed_equity_drawdown(equity_points),
        )

    def run_all_strategies(
        self,
        *,
        points: Sequence[HistoricalPoint],
        candles_by_interval: Mapping[str, Sequence[Candle]],
    ) -> tuple[BacktestReport, ...]:
        names = sorted(
            {
                assessment.strategy
                for point in points
                for assessment in point.assessments
            }
        )
        return tuple(
            self.run_strategy(
                strategy=name,
                points=points,
                candles_by_interval=candles_by_interval,
            )
            for name in names
        )
