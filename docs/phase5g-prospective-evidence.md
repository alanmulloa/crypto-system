# Phase 5G.1 — Automated Prospective Evidence Collection

Phase 5G.1 automates evidence collection for the already-frozen Phase 5G XRP
research candidate. It does not change the strategy and it cannot execute orders.

## Frozen experiment

- Symbol: `XRPUSDT`
- Signal: Mean Reversion `WATCH BUY`
- Feature: `volume_ratio_1h`
- Operator: `<=`
- Threshold: `0.75`
- Frozen cutoff: `1794348615195` (`2026-11-10T22:10:15.195720Z`)
- Outcome horizon: 24h
- Minimum matured candidate observations: 20
- Market source: public Binance data only

Phase 6 remains blocked. `sample_ready=true` is an evidence threshold, not an
approval or automatic promotion rule.

## Scheduled collection

`.github/workflows/phase5g-prospective.yml` runs every six hours and can also
be started manually with `workflow_dispatch`.

Each run:

1. Runs `ruff check app tests` and `pytest -q`.
2. Runs `python -m app.evaluation.prospective_candidate_cli`.
3. Validates the fresh report against the frozen experiment.
4. Compares it with the previous `reports/phase5g/latest.json`.
5. Writes the current report to `latest.json`.
6. Writes a timestamped immutable copy under `reports/phase5g/history/`.
7. Commits only the evidence files back to `main`.

No Binance credentials or repository secrets are required.

## Integrity rules

The collection fails if:

- the frozen cutoff changes;
- symbol, feature, operator, or threshold changes;
- outcome horizon or minimum matured sample changes;
- any observation timestamp is at or before the cutoff;
- a matured observation lacks a full 24h future outcome;
- a previously recorded observation disappears;
- immutable signal/entry fields mutate;
- a matured result mutates;
- a status changes in any way other than `PENDING -> MATURED`.

Pending observations therefore remain present until the evaluator can mature
them from complete future data.

## Evidence layout

```text
agent/reports/phase5g/
├── latest.json
└── history/
    └── <UTC-created-at>.json
```

The history directory is append-only by convention and by the collector's
same-name content check. The workflow is serialized with a concurrency group
to avoid overlapping writers.

## Security boundary

This phase is research-only. It uses public Binance market data and does not
add API keys, private Binance endpoints, Testnet execution, Futures, Margin,
leverage, withdrawals, or order placement.
