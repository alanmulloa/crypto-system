# Phase 5M — Campaign Evidence Durability & Alerts

Phase 5M makes Phase 5L operations durable over the full fixed campaign window.

## 5M.1 Immutable daily operations history

Each Phase 5L.5 operations report is persisted as an immutable timestamped
snapshot plus `latest.json`.

## 5M.2 Continuity / drift gate

A new snapshot is rejected if:

- campaign fingerprint changes
- generated_at does not advance
- an existing timestamped snapshot would be overwritten with different content

## 5M.3 Operational incident detector

Incidents include:

- CAMPAIGN_DRIFT
- MARKET_DATA_UNHEALTHY
- SPOT_UNAVAILABLE
- INTERVAL_GAP
- DUPLICATE_CANDLES
- STALE_CANDLES

Incidents are descriptive/operational only. They never mutate strategy rules.

## 5M.4 Durable repository evidence

Unlike the 30-day workflow artifact retention, Phase 5M commits the durable
operations history to the repository, following the existing Phase 5G pattern.

## 5M.5 Scheduled collection

The workflow runs daily, validates the full test suite, collects public market
health, persists immutable history and updates the incident artifact.

## 5M.6 Guardrails

```text
research_only = true
automatic_strategy_change = false
automatic_registration = false
phase6_blocked = true
```

Phase 5M cannot screen early, register candidates, modify XRP or enable Phase 6.
