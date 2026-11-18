# Phase 5H.9 — Freeze Manifest

Phase 5H.9 creates a deterministic pre-freeze manifest after Phase 5H.8 returns
`READY_FOR_FREEZE`.

The manifest records the exact research definition, evidence references and
SHA-256 fingerprints required for a later human-controlled freeze.

## Contents

- experiment id
- complete rule definition
- calibration and validation periods
- outcome horizon
- fee and slippage assumptions
- calibration artifact path, decision and canonical JSON SHA-256
- validation artifact path, decision and canonical JSON SHA-256
- freeze-review artifact path and SHA-256
- deterministic definition fingerprint
- generation timestamp

The definition fingerprint excludes `freeze_at_ms` because the freeze
timestamp does not exist until the explicit lifecycle transition. The manifest
records:

```text
freeze_at_ms = null
freeze_timestamp_pending = true
```

## Safety

Manifest generation re-runs the Phase 5H.8 readiness checks instead of trusting
the prior gate blindly.

It does not modify the registry, does not set `freeze_at_ms`, and does not
transition the experiment.

```text
research_only = true
auto_transition = false
auto_freeze = false
phase6_blocked = true
```
