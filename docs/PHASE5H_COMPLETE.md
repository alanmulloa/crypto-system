# Phase 5H Completion — Research Infrastructure

Phase 5H now provides a complete research lifecycle around candidate discovery,
validation, freezing and prospective evidence collection.

## Lifecycle

```text
5H.1 registry
→ 5H.2 workspace
→ 5H.3 explicit registration/transitions
→ 5H.4 discovery
→ 5H.5 proposal review
→ 5H.6 calibration
→ 5H.7 validation
→ 5H.8 freeze review
→ 5H.9 freeze manifest
→ explicit human FROZEN transition
→ 5H.10 prospective bootstrap
→ explicit human PROSPECTIVE transition
→ 5H.12 generic signal evaluator
→ 5H.13 public prospective runner
→ 5H.14 multi-experiment planner
→ 5H.15 scheduled orchestration
→ 5H.16 lineage audit
→ 5H.17 human-review dossier
```

## Phase 5G compatibility

The canonical XRP experiment remains on the original Phase 5G pipeline:

```text
XRPUSDT
mean_reversion
BUY
volume_ratio_1h <= 0.75
freeze_at_ms = 1794348615195
outcome_hours = 24
fee = 10 bps
slippage = 5 bps
status = PROSPECTIVE
```

The generic scheduler explicitly excludes this experiment. No automatic
migration has been introduced.

## Safety invariant

Every Phase 5H prospective path keeps:

```text
research_only = true
phase6_eligible = false
phase6_blocked = true
automatic_phase6_promotion = false
execution_enabled = false
testnet_enabled = false
```

Phase 6 remains a separate human decision after genuinely unseen prospective
evidence. Phase 5H never authorizes execution.
