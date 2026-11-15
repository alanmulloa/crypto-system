# Phase 5H.14–5H.15 — Multi-experiment Planning and Orchestration

## 5H.14 Planner

The planner classifies each registry experiment without changing lifecycle
state.

- canonical XRP Phase 5G -> `CONTINUE_EXISTING_PHASE5G`
- generic `FROZEN` -> `BOOTSTRAP_REQUIRED`
- generic `PROSPECTIVE` -> `COLLECT_PROSPECTIVE_EVIDENCE`
- all other lifecycle states -> `NO_PROSPECTIVE_ACTION`

No transition is automatic.

## 5H.15 Batch orchestrator

The batch orchestrator processes only generic `PROSPECTIVE` experiments that
already have a bootstrap artifact. For each eligible experiment it performs:

```text
public Binance candles
→ generic prospective report
→ integrity / continuity gate
→ immutable history + latest
→ monitoring review
→ research decision
```

The canonical XRP experiment is explicitly excluded and remains on Phase 5G.

The GitHub Actions workflow runs every six hours and is safe when no generic
prospective experiment exists: it simply records no generic collection work.

Phase 6 remains blocked and no order/private API capability is introduced.
