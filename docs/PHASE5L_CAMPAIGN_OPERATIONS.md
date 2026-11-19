# Phase 5L — Research Campaign Operations

Phase 5L adds operational monitoring for the fixed Phase 5K research campaign
without evaluating candidate returns before the pre-registered end date.

## 5L.1 Campaign progress

The operations report exposes elapsed days, remaining days, total duration,
completion percentage and the current fixed-window state.

## 5L.2 Public data health

The probe checks only operational market availability:

- Spot availability for all campaign symbols
- recent 15m / 1h / 4h / 1d closed candles
- duplicate open timestamps
- obvious interval gaps
- freshness of the latest closed candle

It does not evaluate candidate outcomes or threshold quality.

## 5L.3 Screening readiness

Screening is operationally ready only after:

- the fixed campaign window has ended
- the campaign fingerprint still matches the pre-registered definition
- public market-data health is valid

The result is `READY_FOR_HUMAN_SCREENING`; screening remains manual.

## 5L.4 Queue awareness

If a Phase 5K promotion queue exists, it is surfaced in the operations
dashboard. No experiment is automatically registered.

## 5L.5 Consolidated operations dashboard

The artifact combines campaign progress, market-data health, screening
readiness, registry counts and the Phase 5K portfolio queue.

## 5L.6 Daily read-only workflow

GitHub Actions generates the operations artifact daily with read-only
repository permissions.

## 5L.7 Guardrails

```text
research_only = true
automatic_screening = false
automatic_registration = false
phase6_blocked = true
```

Phase 5L never modifies XRP Phase 5G and never authorizes Phase 6.
