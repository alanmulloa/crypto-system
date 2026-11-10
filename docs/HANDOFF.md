# HANDOFF - Crypto System after Phase 5B

## Current state

Phases 1-4 are complete. Phase 5A labels future outcomes. Phase 5B adds a deterministic Spot-only backtest simulator for each independent strategy.

## Backtest execution rules

- WATCH only;
- next 1h candle after signal;
- optional entry range validation;
- fixed USD notional;
- Paper Broker fee/slippage assumptions;
- stop / TP1 / horizon;
- stop wins same-candle ambiguity;
- no overlapping trade for the same strategy;
- SELL hypotheses skipped by default (no shorts).

## Metrics

Each strategy report contains:

- trade count;
- gross profit/loss;
- net PnL;
- expectancy;
- profit factor;
- win rate;
- closed-equity max drawdown;
- skipped-signal diagnostics.

## Important interpretation

These results are not yet evidence for Testnet.

The same data can still bias threshold choices.

## Next task - Phase 5C

Split history into calibration / validation / out-of-sample periods and compare performance stability across:

- strategies;
- market regimes;
- horizons/timeframes;
- accepted vs rejected opportunities.

Only after that should the project discuss Binance Spot Testnet credentials.
