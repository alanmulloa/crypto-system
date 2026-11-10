# HANDOFF - Crypto System after Phase 5D tooling

## Current state

Phases 1-4 are complete.

Phase 5 includes:

- 5A outcome labels;
- 5B Spot-only backtest;
- 5C chronological validation;
- 5D real Binance public-history evidence runner.

## New CLI

From `agent/`:

`python -m app.evaluation.evidence_cli`

Default:

- BTCUSDT / ETHUSDT / BNBUSDT / SOLUSDT / XRPUSDT;
- 730 days;
- 8000 hourly evaluation points per symbol;
- output under `reports/`.

## Important parity fix

Historical indicators now default to the same 250-candle depth as the live scanner instead of consuming the entire prior history.

This keeps research closer to production behavior and improves runtime.

## No credentials

5D uses only public Binance klines.

There is still no private exchange client or Testnet execution.

## Next task

Run the evidence CLI against real public history, inspect the generated JSON and produce a Phase 5E evidence review.

Do not start Phase 6 merely because the tooling is complete.
