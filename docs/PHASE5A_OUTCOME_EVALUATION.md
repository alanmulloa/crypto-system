# Phase 5A - Outcome Evaluation

## Goal

Phase 5A answers a research question only:

**What happened after each strategy/aggregate assessment?**

It does not simulate a trade and does not calculate portfolio PnL.

## Inputs

The evaluator reuses Phase 2C `HistoricalPoint`, whose signal-time candidate is constructed only from candles already closed at that timestamp.

Future labels are calculated separately from candles strictly after the signal timestamp.

## Default horizons

- 4h
- 12h
- 24h
- 3d

If the dataset does not contain enough future history for a horizon, that horizon is omitted. No value is extrapolated.

## Metrics per horizon

Raw market-path metrics are always retained:

- exit price;
- raw return;
- maximum upside;
- maximum downside.

For directional BUY/SELL hypotheses, additional direction-aware metrics are calculated:

- directional return;
- MFE (maximum favorable excursion);
- MAE (maximum adverse excursion).

BUY:
- directional return = raw return;
- MFE = max upside;
- MAE = magnitude of max downside.

SELL:
- directional return = negative raw return;
- MFE = magnitude of max downside;
- MAE = max upside.

For WAIT/REJECT assessments without a direction, directional return/MFE/MAE remain null. Raw return/max-up/max-down are still retained so rejected opportunities can be evaluated without inventing a direction.

## Observation levels

Every historical point emits:

1. one aggregate observation;
2. one observation for each independent strategy.

This supports later comparisons such as:

- WATCH vs WAIT vs REJECT;
- trend vs momentum vs mean reversion;
- BUY vs SELL;
- bullish vs bearish/ranging/high-volatility regime.

## Summary helper

`summarize_outcomes()` can filter by:

- source;
- strategy;
- state;
- direction;
- market regime;
- horizon.

It returns:

- observation count;
- directional count;
- average raw return;
- average directional return;
- average MFE;
- average MAE;
- directional hit rate.

These are descriptive diagnostics only. They are not yet a backtest result.

## Persistence

Migration 007 adds `outcome_observations` as an immutable research dataset suitable for later aggregation.

No browser policy or execution path is added.

## Anti-look-ahead boundary

Signal-time candidate construction remains separate from future labeling.

Future candles cannot alter the historical assessment itself.

## Next step - Phase 5B

Build a proper backtest simulator on top of historical assessments and the Paper Broker accounting rules:

- entries/exits;
- fees/slippage;
- stop/TP handling;
- position sizing;
- realized PnL;
- expectancy;
- profit factor;
- drawdown.

Do not tune strategy thresholds on the full dataset.
