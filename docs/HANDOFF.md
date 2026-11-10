# HANDOFF - Crypto System after Phase 5F evidence review

## Current state

Phases 1-4 are complete.

Phase 5 includes:

- 5A outcome labels;
- 5B Spot-only deterministic backtest;
- 5C chronological validation;
- 5D real Binance public-history evidence runner;
- 5E evidence review;
- 5F strategy diagnostics and exit research tooling;
- 5F evidence review completed.

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

The validation improvement at longer horizons is not present in calibration and does not
persist in the already-observed OOS period.

ATR sensitivity also fails to identify a stable positive configuration:

- best pooled calibration: stop 1.0 ATR / target 0.75 ATR, -0.320 USD;
- best pooled validation: stop 2.0 ATR / target 2.0 ATR, -0.042 USD.

Many stopped paths later recover, but changing the exit alone does not solve the
negative calibration evidence.

## Decision

Phase 5G is deferred.

The next task is Phase 5F.1: diagnose Mean Reversion **entry quality** using only
information available at signal time.

Do not select an entry feature using future path information.

Candidate research dimensions:

- score / confidence;
- normalized volatility;
- oversold depth / distance from mean;
- momentum / slope;
- multi-timeframe alignment;
- symbol-specific behavior;
- consecutive-signal clustering / cooldown.

## Methodological boundary

The previous OOS segment has already been observed.

It remains descriptive only and cannot become a fresh OOS test after parameter
selection.

Any eventual Phase 5G candidate must be selected from calibration + validation and then
tested on genuinely unseen future data or prospectively.

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

Implement Phase 5F.1 entry-quality diagnostics for Mean Reversion.

Do not start Phase 6.
