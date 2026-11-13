# Phase 5H.5 — Proposal Review Gate

## Purpose

Phase 5H.5 reviews Phase 5H.4 research proposals before any registration step.
It is deterministic and read-only with respect to the experiment registry.

The gate prevents already-tracked experiments, overlapping research variants,
and statistically weak validation improvements from flowing directly into a new
experiment.

## Pre-registered validation threshold

The minimum validation uplift is fixed at:

```text
0.10 percentage points
```

The threshold is defined before Phase 5H.5 is used to classify proposals. It is
not optimized from the current ETH result.

## Decisions

`ALREADY_TRACKED`
: An exact experiment rule is already present in the registry.

`HUMAN_REVIEW`
: The registry already contains an experiment with the same symbol, strategy,
direction, and feature, but with a different operator or threshold. This avoids
silently creating overlapping variants.

`REJECT_WEAK_VALIDATION`
: The proposal is new but its validation uplift is below 0.10 percentage points.

`READY_TO_REGISTER`
: The proposal is not already tracked, does not overlap an existing research
family, and meets the minimum validation uplift.

A `READY_TO_REGISTER` decision is still not registration. Phase 5H.3 remains
the only explicit registration path.

## Run

From `agent/`:

```bash
python -m app.evaluation.proposal_review_cli \
  --input reports/phase5h4-candidate-discovery.json \
  --registry research/experiment-registry.json \
  --output reports/phase5h5-proposal-review.json
```

For the current canonical registry and the reviewed Phase 5H.4 artifact, the
expected classifications are:

```text
XRPUSDT volume_ratio_1h <= 0.75
-> ALREADY_TRACKED

ETHUSDT structure_4h == lower_highs_lower_lows
-> REJECT_WEAK_VALIDATION
```

The ETH rule passes the broader Phase 5H.4 screen but its validation uplift is
only about 0.011 percentage points, below the pre-registered 0.10 minimum.

## Guardrails

The review artifact records:

```text
research_only = true
auto_register = false
auto_freeze = false
phase6_blocked = true
```

The gate never writes to the registry, never changes a strategy, never freezes
an experiment, and never enables Testnet or live execution.
