# Phase 5F.1 - Mean Reversion Entry Quality Review

## Scope

This review evaluates the real 730-day Phase 5F.1 run for:

- BTCUSDT
- ETHUSDT
- BNBUSDT
- SOLUSDT
- XRPUSDT

The run used 8,000 maximum historical points, a 24h outcome horizon, and a
minimum bucket size of 20 observations.

This is research only. Entry features come from signal-time information. Future
candles are labels only. The previously observed OOS segment is descriptive and
must not be used to select a new rule.

## Pooled result

Pooled 24h net return:

- calibration: -0.8291% across 1,521 observations;
- validation: +0.2596% across 491 observations;
- observed OOS: -0.1780% across 558 observations.

No pooled bucket achieved positive average return in both calibration and
validation.

Six pooled buckets produced positive uplift versus their own segment baselines in
both calibration and validation:

- all four tracked timeframes below EMA20;
- 1h EMA20/EMA50 spread between -2% and -0.5%;
- 1h RSI <= 25;
- 1h lower-highs/lower-lows structure;
- 4h lower-highs/lower-lows structure;
- XRPUSDT.

These are relative improvements, not positive edges. Their calibration average
returns remain negative.

Descriptive OOS behavior was mixed. The four-timeframe-below-EMA condition
remained positive, while several other pooled candidates reversed or weakened.

## Per-symbol result

Only two single-symbol buckets achieved both:

- sufficient sample in calibration and validation; and
- positive average 24h return in both segments.

### ETHUSDT - 4h lower-highs/lower-lows

- calibration: 43 observations, +0.4367%;
- validation: 25 observations, +0.0656%;
- calibration uplift: +1.4487 percentage points;
- validation uplift: +0.0114 percentage points.

This passes the mechanical positive-return screen but validation uplift is almost
zero and the sample is small.

Observed OOS was positive (+0.9846%) but had only 15 observations and is not
eligible for model selection.

Conclusion: secondary research lead only.

### XRPUSDT - 1h volume ratio <= 0.75

- calibration: 55 observations, +0.1651%;
- validation: 27 observations, +0.9975%;
- calibration uplift: +0.5175 percentage points;
- validation uplift: +0.5865 percentage points.

Observed OOS was also positive (+0.1645%) across 31 observations, but this is
descriptive only because OOS had already been observed before Phase 5F.1.

Conclusion: strongest current entry-quality lead, but asset-specific and not yet
a strategy-wide rule.

## Other observations

BTCUSDT, BNBUSDT, and SOLUSDT contain several buckets with stable relative uplift,
but none produce positive average return in both calibration and validation.

The pooled data therefore does not support a universal Mean Reversion entry
filter.

Repeated WATCH BUY clustering also fails to provide a stable general cooldown
rule. The relationship changes materially between calibration and validation.

Score and confidence do not show stable monotonic improvement. Higher score is
not consistently better.

## Decision

Do not create a general Phase 5G Mean Reversion variant yet.

The strongest candidate for the next research step is an asset-specific
diagnostic around:

- XRPUSDT;
- low 1h volume ratio (<= 0.75);
- fixed 24h outcome as the research label.

ETHUSDT 4h lower-highs/lower-lows should remain a secondary comparator.

The next phase should test a narrowly specified candidate without changing the
production strategy. It should compare the candidate against the unchanged
baseline using calibration/validation only and then require genuinely unseen
future or prospective evidence.

Do not use the already observed OOS period as a new validation set.

## Phase 6 status

Phase 6 remains deferred.

No Testnet, private API keys, real orders, Futures, Margin, leverage, or
withdrawals are approved.
