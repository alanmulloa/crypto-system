# HANDOFF - Crypto System after Phase 5F.1 evidence review

## Current state

Phases 1-4 are complete.

Phase 5 includes:

- 5A outcome labels;
- 5B Spot-only deterministic backtest;
- 5C chronological validation;
- 5D real Binance public-history evidence runner;
- 5E evidence review;
- 5F strategy diagnostics and exit research;
- 5F evidence review;
- 5F.1 Mean Reversion entry-quality diagnostics;
- 5F.1 real 730-day evidence review.

## Phase 5F conclusion

Exit tuning alone did not produce stable positive calibration/validation evidence.

## Phase 5F.1 evidence

The 730-day entry-quality run used:

- BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT;
- 8,000 max historical points;
- 24h fixed outcome;
- minimum 20 observations per bucket.

Pooled 24h average net return:

- calibration: -0.8291% (1,521 observations);
- validation: +0.2596% (491 observations);
- observed OOS: -0.1780% (558 observations).

No pooled entry bucket is positive in both calibration and validation.

### Strongest research lead

XRPUSDT with 1h volume ratio <= 0.75:

- calibration: +0.1651% across 55 observations;
- validation: +0.9975% across 27 observations;
- observed OOS: +0.1645% across 31 observations.

OOS is descriptive only and cannot be used to select the rule.

### Secondary lead

ETHUSDT with 4h lower-highs/lower-lows:

- calibration: +0.4367% across 43 observations;
- validation: +0.0656% across 25 observations;
- observed OOS: +0.9846% across 15 observations.

Validation uplift is almost zero and OOS sample is too small, so this remains a
secondary comparator.

## Decision boundary

Do not create a universal Mean Reversion Phase 5G variant.

The next research step, if continued, should be a narrowly specified
asset-specific experimental diagnostic around XRPUSDT low 1h volume conditions,
with ETH as a comparator.

Do not change the production strategy yet.

Do not reuse the already observed OOS period as a new validation set.

Any candidate must eventually be tested on genuinely unseen future data or
prospectively.

## Security boundary

Still absent:

- private exchange credentials;
- Binance Spot Testnet execution;
- real execution;
- Futures;
- Margin;
- leverage;
- withdrawals.

## Phase 5F.2 tooling

Phase 5F.2 compares two predetermined research candidates against the unchanged
Mean Reversion baseline:

- primary: XRPUSDT with `volume_ratio_1h <= 0.75`;
- comparator: ETHUSDT with
  `structure_4h == lower_highs_lower_lows`.

The report includes sample count, coverage, average and median 24h return,
positive-return rate, and uplift versus baseline for calibration, validation and
descriptive OOS.

Only calibration and validation can determine whether a candidate is eligible
for a future prospective test. OOS cannot change that flag.

## Phase 5F.2 review

The reviewed Phase 5F.2 artifact confirms the XRP candidate passed the predefined
calibration/validation screen:

- calibration: 55 observations, +0.1651% average 24h net return, +0.5175 pp uplift;
- validation: 27 observations, +0.9975% average 24h net return, +0.5865 pp uplift.

The ETH comparator also passed mechanically, but validation uplift was only
+0.0114 pp and remains secondary.

The observed OOS results remain descriptive and are not used to select the candidate.

## Phase 5G prospective harness

The XRP candidate is now frozen as:

`XRPUSDT Mean Reversion WATCH BUY with volume_ratio_1h <= 0.75`

Freeze cutoff:

`2026-11-10T22:10:15.195720+00:00`

Only signals strictly after that timestamp may count as prospective evidence.
Pre-freeze candles may be fetched only as indicator lookback.

Run from `agent/`:

```bash
SSL_CERT_FILE="$(python -m certifi)" \
python -m app.evaluation.prospective_candidate_cli \
  --output reports/phase5g-xrp-prospective.json
```

The report tracks baseline XRP Mean Reversion WATCH BUY signals and the frozen
candidate subset, with `PENDING` and `MATURED` 24h outcomes.

`sample_ready` is informational only and does not authorize Testnet or Phase 6.

## Next task

Run the Phase 5G prospective harness now to establish the zero/early baseline, then
rerun it only as genuinely new post-freeze signals mature.

Do not start Phase 6.
