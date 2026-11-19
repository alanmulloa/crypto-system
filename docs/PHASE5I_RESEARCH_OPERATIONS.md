# Phase 5I — Research Operations & Observability

Phase 5I adds operational visibility while prospective evidence accumulates.
It does not alter strategy definitions, experiment lifecycle state or Phase 6.

## 5I.1 Evidence freshness

The latest prospective artifact is classified as:

- `FRESH`
- `STALE`
- `MISSING`
- `MISSING_TIMESTAMP`

The default freshness window is 12 hours, matching the six-hour evidence
collection cadence with room for one delayed run.

## 5I.2 Signal scarcity

Prospective signal availability is described as:

- `NO_CANDIDATE_SIGNAL`
- `CANDIDATE_SIGNAL_SEEN`
- `CANDIDATE_MATURED`

Scarcity is descriptive only. A long period without a candidate signal is not a
reason to change the frozen threshold or strategy.

## 5I.3 Research health

Health combines evidence freshness, signal scarcity and the current research
decision.

Operational states include:

- `HEALTHY_WAITING_FOR_SIGNAL`
- `HEALTHY_WAITING_FOR_MATURITY`
- `HEALTHY_ACCUMULATING_SAMPLE`
- `ATTENTION_STALE_EVIDENCE`
- `ATTENTION_MISSING_EVIDENCE`
- `HUMAN_REVIEW_REQUIRED`

## 5I.4 Research operations queue

The consolidated operations report identifies the next permitted operational
action, such as:

- `CONTINUE_COLLECTION`
- `CHECK_COLLECTION_PIPELINE`
- `HUMAN_RESEARCH_REVIEW`
- `FOLLOW_LIFECYCLE_GATE`

It never writes the experiment registry.

## 5I.5 Scheduled operations report

A GitHub Actions workflow runs every 12 hours, validates the full test suite,
builds `reports/research-ops.json` and uploads it as a workflow artifact.

The workflow is read-only with respect to repository contents.

## 5I.6 Safety invariant

Every operations result keeps:

```text
research_only = true
phase6_blocked = true
automatic_lifecycle_transition = false
automatic_strategy_change = false
```

The current XRP experiment remains frozen at `volume_ratio_1h <= 0.75`.
No absence of signal can mutate that definition automatically.
