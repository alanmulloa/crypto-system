# Phase 5H.2 — Candidate Research Workspace

## Purpose

Phase 5H.2 adds a local, offline workspace for future candidate research without
touching the frozen XRP Phase 5G prospective experiment.

A workspace is allowed only while an experiment is in one of these lifecycle
states:

```text
DRAFT
CALIBRATION
VALIDATION
```

Experiments in `FROZEN`, `PROSPECTIVE`, `COMPLETE`, or `REJECTED`
cannot initialize or validate through this workspace flow. This explicitly keeps
the current XRP 5G experiment outside the new candidate-research path.

## Workspace layout

From the `agent/` directory, initializing an eligible experiment creates:

```text
research/workspaces/<experiment-id>/
├── workspace.json
├── artifacts/
└── notes/
```

The manifest stores a deterministic snapshot of the experiment definition and
hard guardrails:

```text
research_only = true
phase6_blocked = true
workspace_kind = candidate-research
```

It does not store credentials and does not call Binance or Supabase.

## CLI

Initialize:

```bash
python -m app.evaluation.candidate_workspace_cli init <experiment-id>
```

Validate against the current registry:

```bash
python -m app.evaluation.candidate_workspace_cli validate <experiment-id>
```

Inspect:

```bash
python -m app.evaluation.candidate_workspace_cli show <experiment-id>
python -m app.evaluation.candidate_workspace_cli --json show <experiment-id>
```

Initialization is idempotent when the existing manifest exactly matches the
registered definition. If the workspace definition has drifted from the
registry, validation fails explicitly.

## XRP isolation

The existing `phase5g-xrp-low-volume-1h` entry is `PROSPECTIVE`.
Phase 5H.2 therefore refuses to initialize a candidate workspace for it.

No Phase 5G artifact, cutoff, threshold, fee/slippage assumption, strategy rule,
prospective observation, or decision protocol is changed.

## Security boundary

Phase 5H.2 is research-only infrastructure. It does not:

- fetch market data;
- run candidate discovery;
- place orders;
- use Binance private APIs;
- enable Testnet;
- enable Futures, Margin, leverage, or withdrawals;
- unblock Phase 6.
