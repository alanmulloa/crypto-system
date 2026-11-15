# Phase 5H.10 — Generic Prospective Bootstrap

Phase 5H.10 adds a generic adapter layer for future frozen experiments without
modifying the existing XRP Phase 5G implementation.

## Bootstrap contract

A protocol can be created only from an experiment with:

```text
status = FROZEN
freeze_at_ms != null
```

The protocol is derived from the registry and a Phase 5H.9 freeze manifest.
It locks:

- symbol / strategy / direction
- feature / operator / threshold
- freeze cutoff
- outcome horizon
- fee and slippage assumptions
- minimum matured sample
- definition fingerprint

## Prospective evidence boundary

Generic reports must contain only observations with:

```text
signal_timestamp_ms > frozen_at_ms
```

Pre-freeze market data may be used by a future producer only for indicator
lookback. It cannot appear as a prospective outcome observation.

Matured observations must cover the complete registry-defined outcome horizon.

## Persistence

The generic collection gate provides:

- immutable history snapshots
- latest snapshot
- no disappearing prior observations
- immutable signal/entry fields
- only PENDING -> MATURED status progression
- immutable matured outcomes

The layer does not fetch market data and does not yet replace the XRP-specific
5G evaluator. A future signal producer can target this report contract.

## Guardrails

```text
research_only = true
phase6_blocked = true
execution_enabled = false
testnet_enabled = false
automatic_promotion = false
```

Existing Phase 5G remains unchanged.
