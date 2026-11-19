# Phase 5V–5Z — Unified Research Control Plane

This macro-block gives the research system one consolidated operational view.

## Phase 5V — Unified Research State

The control plane combines:

- experiment registry
- XRP Phase 5G review and decision
- campaign governance when available
- writer policy when available

Missing downstream artifacts are represented explicitly instead of guessed.

## Phase 5W — Blocker Graph

The snapshot lists blockers such as:

- prospective sample incomplete
- campaign governance not yet available
- writer-policy noncompliance

These are informational only and cannot mutate research state.

## Phase 5X — Human Action Inbox

Only explicit human-action items are surfaced, including:

- human Phase 6 research review
- failed-research review
- campaign incident review
- fixed campaign screening after maturity

## Phase 5Y — Material State Change Detection

The control plane compares the current state with the previous snapshot while
ignoring timestamp-only changes. This reduces noisy operational review.

## Phase 5Z — Research Control-Plane Completion

A single snapshot reports:

- overall state
- experiments
- campaign state
- writer policy
- blockers
- human-action inbox
- snapshot SHA-256

Guardrails remain:

```text
research_only = true
automatic_strategy_change = false
automatic_registration = false
automatic_screening = false
automatic_freeze = false
automatic_phase6_activation = false
phase6_eligible = false
phase6_blocked = true
```

The workflow is read-only and produces artifacts only.
