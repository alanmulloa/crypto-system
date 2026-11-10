# Phase 5C - Temporal Validation

## Goal

Phase 5C separates research evidence into chronological:

1. calibration;
2. validation;
3. out-of-sample.

Default split:

- 60% calibration;
- 20% validation;
- 20% out-of-sample.

The split is never shuffled.

## Segment leakage protection

Each segment receives only candles whose close timestamp is less than or equal to that segment's end timestamp.

Therefore:

- calibration trades/outcomes cannot use validation prices;
- validation cannot use out-of-sample prices;
- signals near a boundary may be skipped when their future exit/outcome is unavailable.

This is intentional.

## Per-strategy validation

Each independent strategy is evaluated separately using the Phase 5B Spot backtest.

The report keeps:

- calibration backtest;
- validation backtest;
- out-of-sample backtest;
- expectancy sign consistency;
- out-of-sample expectancy vs calibration ratio;
- out-of-sample drawdown degradation.

These diagnostics do not automatically promote or disable a strategy.

## Regime diagnostics

Backtest trades are grouped by signal-time market regime:

- bullish;
- bearish;
- ranging;
- high volatility;
- unknown.

For each regime:

- trades;
- net PnL;
- expectancy;
- win rate.

## Score sensitivity

For each segment, WATCH observations are compared at score bands:

- 65;
- 70;
- 75;
- 80;
- 85.

This does not rewrite strategy thresholds.

It only checks whether apparent performance is stable or depends on a narrow score cutoff.

## Rejected-signal diagnostics

Phase 5A outcomes are summarized separately for WATCH and REJECT observations inside each segment.

This can reveal cases where rejected setups systematically outperform accepted ones.

No rejected signal is executed.

## What 5C does not do

- no automatic parameter optimization;
- no automatic strategy weighting;
- no Testnet activation;
- no API keys;
- no real trading.

## Persistence

Migration 009 adds `validation_runs` for research diagnostics.

## Evidence interpretation

A strategy should not be considered robust merely because calibration is profitable.

Warning signs include:

- expectancy changes sign in validation/OOS;
- profit factor collapses;
- drawdown rises sharply;
- only one market regime carries the result;
- performance disappears with small score-threshold changes;
- rejected outcomes look better than WATCH outcomes.

## Next step

The next work should be **running Phase 5 against sufficiently deep real Binance history** and reviewing the evidence.

Only after enough out-of-sample observations and prospective Paper results should Phase 6 Binance Spot Testnet be considered.
