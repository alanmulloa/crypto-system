# HANDOFF - Crypto System after Phase 5A

## Current state

Phases 1-4 are implemented. Phase 5A adds future-outcome labeling for historical research observations.

## What 5A measures

For every historical point:

- aggregate assessment outcome;
- each strategy assessment outcome;
- 4h / 12h / 24h / 3d future path when available;
- raw return;
- max upside/downside;
- direction-aware return/MFE/MAE for BUY/SELL.

WAIT/REJECT without direction still keep raw future market movement.

## What 5A does not do

It does not claim trading profitability.

There is no:

- position sizing;
- entry fill simulation;
- stop/TP execution;
- fee-adjusted PnL;
- equity curve;
- drawdown.

Those belong to Phase 5B.

## No-look-ahead

HistoricalPoint remains the signal-time boundary. OutcomeEvaluator only labels candles strictly after that timestamp.

## Persistence

Migration 007 introduces `outcome_observations` for immutable research labels.

## Next task - Phase 5B

Implement a backtest simulator using the same deterministic fee/slippage assumptions as Paper Broker, then calculate trade/equity metrics.

Keep calibration and out-of-sample validation separate; do not optimize on the full dataset.
