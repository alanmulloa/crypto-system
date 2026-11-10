# Phase 2C - Historical Sanity

## Purpose

Phase 2C adds a walk-forward historical evaluator before portfolio/risk integration.

It is intentionally **not** a profitability backtester. It does not simulate capital, fills, fees, slippage, or orders.

Its first job is to prove that the strategy layer behaves deterministically and cannot access future candles.

## Historical visibility rule

For a historical evaluation timestamp `T`, every timeframe is truncated to candles satisfying:

`candle.close_time_ms <= T`

Only then are indicators, market regime, independent strategies and aggregation evaluated.

Future candles are never passed to the strategy layer.

## Runner

`HistoricalSanityRunner`:

1. chooses an anchor timeframe (1h by default);
2. walks through historical anchor close timestamps;
3. truncates 15m/1h/4h/1d independently at that timestamp;
4. requires indicator warmup on every timeframe;
5. rebuilds a `MarketCandidate`;
6. evaluates all five Phase 2A strategies;
7. runs the Phase 2B aggregator;
8. records an immutable `HistoricalPoint`.

The runner does not use Phase 1 `ranking_score` and does not call Risk Manager or execution.

## Diagnostics

`summarize()` reports:

- number of historical points;
- aggregate WATCH / WAIT / REJECT counts;
- unresolved directional conflicts;
- WATCH / WAIT / REJECT counts per strategy.

These diagnostics are intended to reveal pathological behavior such as:

- a strategy that always WATCHes;
- a strategy that never activates;
- excessive unresolved conflicts;
- unstable state changes.

They do not establish profitability.

## No-look-ahead regression test

The test suite evaluates a timestamp, then changes candles that occur only after that timestamp. Candidate, strategy assessments and aggregate output must remain exactly equal.

This regression is a hard safety property for future backtesting.

## What Phase 2C does not do

- no optimization;
- no parameter search;
- no PnL;
- no Sharpe;
- no win rate;
- no order simulation;
- no paper trading;
- no private Binance API.

Those belong to later phases after portfolio/risk integration and a dedicated backtesting/evaluation layer.

## Next step

Phase 3 should connect the existing tracker portfolio to the agent and upgrade the Risk Manager while preserving hard limits outside strategy control.
