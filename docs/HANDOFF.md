# HANDOFF - Crypto System after Phase 5F tooling

## Current state

Phases 1-4 are complete.

Phase 5 includes:

- 5A outcome labels;
- 5B Spot-only deterministic backtest;
- 5C chronological validation;
- 5D real Binance public-history evidence runner;
- 5E evidence review;
- 5F strategy diagnostics and exit research tooling.

## Evidence conclusion before 5F

The 730-day run across BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT and XRPUSDT showed
negative aggregate OOS backtest results for all five current strategies.

Mean Reversion remains the main research lead because WATCH outcomes showed a positive
directional signal while realized backtest mechanics remained negative.

This is a research hypothesis, not an approved strategy.

## Phase 5F CLI

From `agent/`:

```bash
python -m app.evaluation.diagnostics_cli \
  --days 730 \
  --symbols BTCUSDT ETHUSDT BNBUSDT SOLUSDT XRPUSDT \
  --strategy mean_reversion \
  --max-points 8000 \
  --output reports/phase5f-mean-reversion.json
```

Defaults:

- public Binance Spot market data only;
- fee 10 bps;
- slippage 5 bps;
- 24h current-exit horizon;
- 48h research path;
- up to 25 individual path examples per segment in JSON.

## Methodological boundary

The previous OOS segment has already been observed.

Do not tune against it and then label it OOS again.

ATR sensitivity rows on OOS are descriptive and carry
`research_eligible=false`.

Any selected experimental configuration must later be tested on genuinely unseen
future data or prospectively.

## Strategy integrity

Phase 5F does not modify the generation rules in
`agent/app/strategies/mean_reversion.py` or any other strategy.

It adds diagnostics only.

## Security boundary

Still absent:

- private exchange credentials;
- Binance Spot Testnet execution;
- real execution;
- Futures;
- Margin;
- leverage;
- withdrawals.

## Next task

Run Phase 5F on the same 730-day public dataset, inspect the JSON, and decide whether
there is enough evidence to define one narrow Phase 5G experimental variant.

Do not start Phase 6 from the Phase 5F tooling alone.
