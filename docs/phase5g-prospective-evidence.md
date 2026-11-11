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


# Phase 5G.2 — Monitoring & Review

Phase 5G.2 converts the latest prospective evidence into a deterministic review
summary. It does not alter the frozen candidate and it cannot authorize Phase 6.

Each collection run also executes:

```bash
python -m app.evaluation.prospective_review \
  --input reports/phase5g/latest.json \
  --output reports/phase5g/review.json
```

The review exposes:

- baseline and candidate observation/pending/matured counts;
- progress toward 20 matured candidate observations;
- current return, median, positive-rate, and uplift metrics when available;
- milestones for first baseline signal, first candidate signal, first matured
  candidate observation, and sample readiness;
- a monitoring state and a decision gate.

The only automated decisions are:

- `WAIT`: prospective evidence is still incomplete;
- `REVIEW`: the minimum matured sample has been reached and a human review is
  required.

There is deliberately no automatic `PASS`. Even when `sample_ready=true`,
`phase6_blocked` remains true until a separate formal decision is made.


# Phase 5G.3 — Prospective Decision Protocol

Phase 5G.3 pre-registers the final prospective research decision before the
candidate has accumulated the minimum sample. This prevents criteria from being
changed after observing the results.

The protocol reads `reports/phase5g/latest.json` and writes
`reports/phase5g/decision.json`.

## Frozen decision criteria

A research pass requires all of the following:

- at least 20 matured candidate observations;
- candidate average net return > 0;
- candidate median net return > 0;
- candidate positive return rate > 50%;
- uplift versus baseline > 0;
- historical integrity validation succeeds;
- the frozen experiment validation succeeds.

Decision states:

- `NOT_READY`: fewer than 20 matured candidate observations;
- `INCONCLUSIVE`: minimum sample reached but at least one required metric is
  unavailable;
- `PASS_RESEARCH`: minimum sample reached and every pre-registered metric
  passes;
- `FAIL_RESEARCH`: minimum sample reached and at least one available criterion
  fails.

`PASS_RESEARCH` is not an execution approval. `phase6_eligible` and
`phase6_blocked` remain false/true respectively until a separate human review
explicitly authorizes the next phase. No strategy, fee, slippage, order, Testnet,
private API, Futures, Margin, leverage, or withdrawal behavior is changed here.
