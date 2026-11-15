# Phase 5H.8 — Freeze Review Protocol

Phase 5H.8 is the final retrospective gate before a human-controlled transition
from `VALIDATION` to `FROZEN`.

It requires the calibration and validation artifacts to contain full
`experiment_definition` snapshots. Phase 5H.6 and 5H.7 now emit these
snapshots. Older artifacts without them are treated as `INCONCLUSIVE`, never
as freeze-ready.

## Decisions

- `READY_FOR_FREEZE`
- `NOT_READY_FOR_FREEZE`
- `INCONCLUSIVE`

`READY_FOR_FREEZE` requires:

- registry status = `VALIDATION`
- calibration artifact integrity valid
- calibration decision = `PASS_CALIBRATION`
- validation artifact integrity valid
- validation decision = `PASS_VALIDATION`
- exact definition equality across registry and both artifacts
- `freeze_at_ms = null`

Definition equality includes symbol, strategy, direction, feature, operator,
threshold, calibration/validation periods, outcome horizon, fees and slippage.

The gate is read-only. It never writes the registry and never performs the
`FROZEN` transition.

## CLI

```bash
python -m app.evaluation.freeze_review_cli \
  --registry research/experiment-registry.json \
  --experiment-id <id> \
  --calibration-artifact <phase5h6.json> \
  --validation-artifact <phase5h7.json> \
  --output reports/phase5h8-freeze-review.json
```

Guardrails remain:

```text
research_only = true
auto_transition = false
auto_freeze = false
phase6_blocked = true
```
