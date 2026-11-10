# Phase 5D - Real Historical Evidence Runner

## Purpose

Phase 5D runs the existing Phase 5 research stack against deep **public Binance Spot kline history**.

It still does not introduce credentials, Testnet or real orders.

## Binance endpoint

The runner uses only:

`GET /api/v3/klines`

with:

- symbol;
- interval;
- startTime;
- endTime;
- limit <= 1000.

Historical downloads are paginated, deduplicated by candle open time and filtered to fully closed candles.

## Default evidence universe

The CLI defaults to:

- BTCUSDT
- ETHUSDT
- BNBUSDT
- SOLUSDT
- XRPUSDT

These are an initial liquid-asset research universe, not an allow-list for future execution.

## Default history

- 730 calendar days requested;
- 15m / 1h / 4h / 1d downloaded;
- up to 8000 most recent hourly evaluation points per symbol.

CLI:

`python -m app.evaluation.evidence_cli`

Example:

`python -m app.evaluation.evidence_cli --days 730 --symbols BTCUSDT ETHUSDT --max-points 8000 --output reports/evidence.json`

## Historical/live parity correction

Before Phase 5D, HistoricalSanityRunner supplied all prior candles to indicators, while the live scanner normally fetches 250.

Phase 5D changes the historical default to:

`analysis_candles=250`

using binary-search slicing.

This improves both:

- parity with live behavior;
- runtime scalability.

The anti-look-ahead rule is unchanged: only candles closed at or before the historical timestamp are visible.

## Data-quality diagnostics

Every symbol records, per interval:

- candle count;
- first open;
- last close;
- duplicate open times;
- detected gaps.

Gaps are reported rather than silently filled.

## Evidence produced

For every symbol and every strategy, the report contains the Phase 5C structure:

- calibration;
- validation;
- out-of-sample;
- backtest metrics;
- WATCH vs REJECT outcomes;
- regime diagnostics;
- score sensitivity;
- stability diagnostics.

## Interpretation

The runner produces evidence, not an automatic approval.

Do not advance a strategy merely because one symbol or one segment is profitable.

Review at least:

- trade sample sizes;
- OOS expectancy;
- profit factor;
- drawdown;
- regime concentration;
- score sensitivity;
- rejected-signal outcomes;
- consistency across assets.

## Security

Phase 5D has:

- no API key;
- no signed request;
- no private endpoint;
- no Testnet;
- no execution;
- no Futures/Margin/leverage/withdrawals.

## Next decision

After a real evidence JSON is generated and reviewed, decide whether:

1. strategies need another research iteration;
2. prospective Paper monitoring should continue longer;
3. evidence is strong enough to begin designing Phase 6 Spot Testnet.

The decision must be evidence-based, not roadmap-driven.
