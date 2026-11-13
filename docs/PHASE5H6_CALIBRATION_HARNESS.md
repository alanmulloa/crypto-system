# Phase 5H.6 — Calibration Harness

## Purpose

Phase 5H.6 evaluates a registered candidate while it is explicitly in
`CALIBRATION` state.

The harness is deliberately isolated from validation and out-of-sample evidence.
It reads only the `calibration` bucket summary from an existing Phase 5F.1
artifact.

It does not collect new market data, change the registry, transition lifecycle
state, freeze a candidate, or authorize Phase 6.

## Pre-registered calibration criteria

The calibration decision is fixed before running new candidates.

A candidate passes calibration only if all of the following are true:

```text
observations >= 20
average return > 0
median return > 0
positive return rate > 50%
uplift vs calibration baseline > 0
```

Results:

```text
PASS_CALIBRATION
FAIL_CALIBRATION
INCONCLUSIVE
```

`PASS_CALIBRATION` means only that the candidate is eligible for a separate
human-controlled transition to `VALIDATION`. The harness never performs that
transition.

## Rule resolution

Phase 5H.6 accepts only definitions that map exactly to the pre-defined Phase
5F.1 buckets used by Phase 5H.4 discovery.

For example:

```text
volume_ratio_1h <= 0.75 -> bucket <=0.75
rsi_1h <= 25 -> bucket <=25
structure_4h == lower_highs_lower_lows
  -> bucket lower_highs_lower_lows
```

An arbitrary threshold such as `volume_ratio_1h <= 0.73` is rejected instead
of being re-bucketed or optimized after seeing results.

## Run

From `agent/`:

```bash
python -m app.evaluation.calibration_harness_cli \
  --input reports/phase5f1-mean-reversion.json \
  --registry research/experiment-registry.json \
  --experiment-id <registered-calibration-experiment> \
  --output reports/phase5h6-calibration.json
```

The registered experiment must already have:

```text
status = CALIBRATION
```

## Leakage boundary

The generated artifact explicitly records:

```text
segment_used = calibration
validation_read = false
oos_read = false
```

Validation evidence is reserved for the later validation harness.

## Guardrails

The artifact also records:

```text
research_only = true
auto_transition = false
phase6_blocked = true
```

XRP Phase 5G is `PROSPECTIVE`, so it cannot enter the calibration harness.
