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

## Next task

Design a research-only Phase 5F.2/5G candidate experiment for the XRPUSDT low-volume
entry condition against the unchanged Mean Reversion baseline.

Do not start Phase 6.
