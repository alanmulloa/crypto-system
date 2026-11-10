# Phase 5B - Deterministic Spot Backtest

## Goal

Phase 5B answers:

**What would have happened if each strategy's WATCH signals were executed under explicit Spot-only rules?**

This is different from Phase 5A, which only labeled future market outcomes.

## Scope

The simulator runs each strategy independently.

Default execution model:

- WATCH only;
- directional hypothesis required;
- Spot-only: SELL hypotheses are skipped by default;
- one open trade per strategy at a time;
- entry on the first 1h candle strictly after the signal;
- optional strategy entry range must contain that candle's open;
- fixed USD notional;
- same fee/slippage assumptions as the Paper Broker;
- strategy stop and TP1 are honored;
- otherwise close at max holding horizon.

## No-look-ahead

Signal data comes from HistoricalPoint.

The entry candle must open strictly after the signal timestamp.

No future candle changes the signal itself.

## Intrabar ambiguity

If a candle touches both stop and TP1, the simulator assumes **STOP first**.

This is deliberately conservative because OHLC data does not reveal intrabar path order.

## Spot-only boundary

SELL hypotheses are not modeled as shorts.

They are always skipped by the backtest simulator. This preserves the project constraint of no Margin/no short selling.

Phase 5A still measures bearish SELL hypotheses as research outcomes.

## Fees and slippage

BUY entry:
- execution price = market open x (1 + slippage)

SELL exit:
- execution price = exit reference x (1 - slippage)

Fees are charged on entry notional and exit gross proceeds.

## Metrics

Per strategy:

- trades;
- wins/losses;
- gross profit;
- gross loss;
- net PnL;
- expectancy;
- profit factor;
- win rate;
- closed-equity max drawdown;
- skipped WATCH/non-WATCH/SELL/no-entry/overlap/no-exit counts.

The drawdown is currently based on closed-trade equity, not intratrade mark-to-market.

## Entry-range behavior

When `require_entry_range=true`, a signal is only considered filled when the next 1h open is between the strategy's `entry_low` and `entry_high`.

This avoids assuming fills at stale signal prices after a gap.

## Persistence

Migration 008 introduces research-only:

- `backtest_runs`
- `backtest_trades`

RLS is enabled.

## Next step - Phase 5C

Validation must separate data into calibration, validation and out-of-sample segments.

Do not pick strategy weights or thresholds from the same full history used to report performance.
