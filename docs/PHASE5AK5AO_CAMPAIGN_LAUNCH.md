# Phase 5AK–5AO — Campaign Launch Guard

This macro-block formally seals and verifies the Phase 5K campaign launch.

## Phase 5AK — Pre-registered Launch Seal

A versioned launch-seal file contains the exact campaign definition that must
remain unchanged at launch and throughout the fixed research window.

## Phase 5AL — Definition Integrity Gate

Each Phase 5M cycle compares the live campaign definition against the sealed
definition and both deterministic fingerprints. Any drift becomes:

```text
BLOCKED_DEFINITION_DRIFT
```

## Phase 5AM — Pre-start Readiness

Before the start timestamp, the launch state is either:

- PRESTART_READY
- PRESTART_DATA_ATTENTION

depending only on public market-data health.

## Phase 5AN — First-Day Smoke Check

During the first 24 hours after the fixed start timestamp, the launch state is:

- FIRST_DAY_HEALTHY
- FIRST_DAY_ATTENTION

No strategy outcomes are evaluated by this check.

## Phase 5AO — Launch Completion Guardrails

After launch, the state becomes COLLECTING until the fixed campaign end.
Screening before the end remains forbidden and no automatic lifecycle action is
introduced.

```text
threshold_optimization_forbidden = true
automatic_screening = false
automatic_registration = false
automatic_freeze = false
phase6_eligible = false
phase6_blocked = true
```
