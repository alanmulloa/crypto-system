# Phase 5H.7 — Validation Harness

## Purpose

Phase 5H.7 evaluates a registered candidate while it is explicitly in
`VALIDATION` state.

The harness reads only the `validation` bucket summary from an existing Phase
5F.1 artifact. Calibration and out-of-sample evidence are not used to make the
validation decision.

The harness never freezes an experiment automatically.

## Pre-registered validation criteria

A candidate passes validation only if all of these are true:

```text
observations >= 20
average return > 0
median return > 0
positive return rate > 50%
uplift vs validation baseline >= 0.10 percentage points
```

Possible results:

```text
PASS_VALIDATION
FAIL_VALIDATION
INCONCLUSIVE
```

`PASS_VALIDATION` means only that the experiment is eligible for a separate
human freeze review. It does not transition the registry and does not create a
prospective experiment.

## Rule resolution

As in Phase 5H.6, the registered rule must map exactly to a pre-defined Phase
5F.1 bucket. Arbitrary thresholds are rejected rather than approximated.

## Run

From `agent/`:

```bash
python -m app.evaluation.validation_harness_cli \
  --input reports/phase5f1-mean-reversion.json \
  --registry research/experiment-registry.json \
  --experiment-id <registered-validation-experiment> \
  --output reports/phase5h7-validation.json
```

The experiment must already have:

```text
status = VALIDATION
```

## Leakage boundary

The generated artifact records:

```text
segment_used = validation
calibration_read = false
oos_read = false
```

The harness does not use calibration or OOS results to determine
`PASS_VALIDATION`.

## Guardrails

The artifact also records:

```text
research_only = true
auto_transition = false
phase6_blocked = true
```

A successful validation still requires a separate human review before any
transition to `FROZEN`. Phase 6 remains blocked.
