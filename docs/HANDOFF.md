# HANDOFF - Crypto System after Phase 5F.1 tooling

## Current state

Phases 1-4 are complete.

Phase 5 includes:

- 5A outcome labels;
- 5B Spot-only deterministic backtest;
- 5C chronological validation;
- 5D real Binance public-history evidence runner;
- 5E evidence review;
- 5F strategy diagnostics and exit research tooling;
- 5F evidence review;
- 5F.1 Mean Reversion entry-quality diagnostics tooling.

## Phase 5F conclusion

The 730-day Mean Reversion diagnostic run does **not** justify a Phase 5G exit-tuning
variant.

Across all five symbols, pooled net expectancy per $100 research observation was:

- calibration current exit: -0.426 USD;
- calibration best fixed horizon (4h): -0.324 USD;
- validation 24h: +0.267 USD;
- validation 48h: +1.206 USD;
- observed OOS 24h: -0.178 USD;
- observed OOS 48h: -0.434 USD.

ATR sensitivity also failed to identify a stable positive calibration/validation
configuration.

## Phase 5F.1 tooling

The entry-quality analyzer uses only information available at signal time.

It reports predetermined buckets for:

- score and confidence;
- 1h RSI, ATR%, volume ratio and EMA distance;
- 1h EMA20/EMA50 spread;
- 15m RSI / EMA distance;
- 4h RSI / EMA distance;
- count of tracked timeframes below EMA20;
- 1h / 4h market structure;
- symbol;
- time since the previous Mean Reversion WATCH BUY;
- WATCH BUY count in the previous six hours.

Future candles are labels only.

Cross-segment candidate flags use calibration + validation only. The already-observed
OOS segment is descriptive and cannot influence candidate selection.

## Run Phase 5F.1

From `agent/`:

```bash
python -m app.evaluation.entry_quality_cli \
  --days 730 \
  --symbols BTCUSDT ETHUSDT BNBUSDT SOLUSDT XRPUSDT \
  --max-points 8000 \
  --outcome-hours 24 \
  --min-bucket-observations 20 \
  --output reports/phase5f1-mean-reversion.json
```

The JSON contains per-symbol reports and a pooled five-symbol report.

## Promotion boundary

Do not create Phase 5G merely because one bucket is positive.

A candidate entry rule should have useful sample size and consistent
calibration/validation evidence, preferably across multiple symbols.

Any selected Phase 5G variant must then be tested on genuinely unseen future data or
prospectively before Phase 6 can be considered.

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

Run Phase 5F.1 on the same 730-day public dataset and review the JSON.

Do not start Phase 6.
