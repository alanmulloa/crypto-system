# Phase 5F.1 - Mean Reversion Entry Quality Diagnostics

## Purpose

Phase 5F showed that changing exits alone does not produce stable positive evidence
across calibration and validation. Phase 5F.1 therefore inspects entry quality.

This phase is research only. It does not modify strategy rules and cannot place orders.

## Leakage boundary

Every feature in this report comes from the historical `MarketCandidate` and strategy
assessment available at the signal timestamp.

Future candles are used only to label the selected fixed outcome horizon.

The previously observed OOS segment remains descriptive only.

## Signal-time features

The report includes deterministic, predetermined buckets for:

- strategy score and confidence;
- 1h RSI;
- 1h ATR percentage;
- 1h volume ratio;
- price distance from 1h EMA20;
- 1h EMA20/EMA50 spread;
- 15m RSI and distance from EMA20;
- 4h RSI and distance from EMA20;
- number of tracked timeframes below EMA20;
- 1h and 4h market structure;
- symbol;
- hours since the previous Mean Reversion WATCH BUY;
- WATCH BUY signal count during the previous six hours.

Buckets are fixed in code rather than optimized from the observed returns.

## Cross-segment screen

Candidate evidence is computed from calibration + validation only.

A bucket is marked as:

- `stable_positive_uplift` when both calibration and validation beat their own
  segment baselines and both samples meet the minimum observation count;
- `stable_positive_return` when average fixed-horizon return is positive in both
  calibration and validation and both samples meet the minimum observation count.

These flags are research screens, not strategy approvals.

## Run

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

The output contains per-symbol reports plus a pooled five-symbol report.

## Promotion rule

Do not create Phase 5G merely because one bucket looks good.

A narrow entry rule is justified only when the same pre-specified condition has useful
sample size and consistent calibration/validation evidence, preferably across more than
one symbol. Any selected variant must then be evaluated on genuinely unseen future data
or prospectively before Phase 6 can be considered.
