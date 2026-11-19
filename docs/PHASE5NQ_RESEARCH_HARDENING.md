# Phase 5N–5Q — Research Operations Hardening

This macro-block hardens the fixed Phase 5K campaign without modifying its
research definition or advancing Phase 6.

## Phase 5N — Incident Response & Recovery

Operational incidents are mapped to explicit human-reviewed recovery actions.

Recovery is never automatic and cannot:

- change strategy rules
- change thresholds
- write the experiment registry
- enable Testnet or live execution

## Phase 5O — Reproducibility

A deterministic SHA-256 manifest fingerprints:

- the pre-registered campaign definition
- latest durable operations report
- incident report
- recovery plan

The manifest can be verified against the exact same inputs.

## Phase 5P — Human Review Pack

The review pack consolidates:

- campaign progress
- screening readiness
- incident severity
- recovery actions
- reproducibility manifest

States include:

- COLLECTING
- ATTENTION_INCIDENTS
- BLOCKED_CRITICAL_INCIDENT
- READY_FOR_HUMAN_SCREENING

Screening remains manual.

## Phase 5Q — Operations Completion / Hardening

The governance artifact records whether campaign operations are healthy and
reproducible while preserving all guardrails.

```text
automatic_strategy_change = false
automatic_screening = false
automatic_registration = false
automatic_freeze = false
phase6_eligible = false
phase6_blocked = true
```

The scheduled workflow is read-only and produces review artifacts only.
