# Phase 5AA–5AE — Durable Research Control Plane

This macro-block fixes a cross-run state gap in Phase 5V–5Z.

## Phase 5AA — Durable Control-Plane State

The control-plane workflow now persists its last material snapshot to the
repository, so the next scheduled run can compare against real prior state.

## Phase 5AB — Material Transition Ledger

Only material state changes create immutable history/event records.
Timestamp-only churn produces no repository commit.

## Phase 5AC — Stable Human-Action / Blocker IDs

Human actions and blockers receive deterministic IDs derived from type/code and
subject. The same unresolved action keeps the same identifier across runs.

## Phase 5AD — Main-Writer Integration

The control-plane workflow becomes the fourth audited research writer:

- shared `research-main-writer` concurrency group
- `cancel-in-progress: false`
- full-history checkout
- `git pull --rebase origin main`
- explicit `HEAD:main` push
- no force push

## Phase 5AE — Control-Plane Durability Completion

The control plane can now distinguish:

- first snapshot
- no material change
- real state transition

while preserving:

```text
research_only = true
automatic strategy/lifecycle changes = false
phase6_eligible = false
phase6_blocked = true
```
