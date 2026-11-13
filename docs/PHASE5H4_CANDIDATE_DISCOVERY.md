# Phase 5H.4 — Candidate Discovery

## Purpose

Phase 5H.4 converts existing Phase 5F.1 entry-quality evidence into deterministic
research proposals. It does not register, freeze, execute, or promote anything.

The input is an already-generated Phase 5F.1 artifact. Historical public Binance
collection remains the responsibility of the existing Phase 5F.1 tooling.

This separation prevents Phase 5H.4 from introducing a second market-data path.

## Selection boundary

Discovery uses only:

- per-symbol Phase 5F.1 cross-segment evidence;
- calibration;
- validation;
- buckets pre-defined in Phase 5F.1 code.

Previously observed out-of-sample evidence is not used for selection.

A proposal requires all three existing Phase 5F.1 flags:

```text
sufficient_sample_both = true
stable_positive_return = true
stable_positive_uplift = true
```

There is no threshold optimization in Phase 5H.4.

Only buckets that can be represented exactly as a simple rule are eligible.
Examples include:

```text
volume_ratio_1h <= 0.75
rsi_1h <= 25
ema_spread_pct_1h >= 0.5
structure_4h == lower_highs_lower_lows
```

Middle-range buckets such as `0.75-1.5` are deliberately ignored because they
cannot be represented by the registry's single operator/threshold definition
without changing its semantics.

## Run

First produce or reuse a Phase 5F.1 artifact. Then:

```bash
python -m app.evaluation.candidate_discovery_cli \
  --input reports/phase5f1-mean-reversion.json \
  --output reports/phase5h4-candidate-discovery.json
```

The output contains research proposals sorted by validation uplift and validation
return.

Each proposal includes:

- deterministic proposal id;
- symbol;
- strategy and direction;
- feature/operator/threshold;
- outcome horizon;
- calibration/validation sample counts;
- calibration/validation average return;
- calibration/validation uplift;
- `recommendation = RESEARCH_CANDIDATE`.

## Hard guardrails

Every output records:

```text
research_only = true
auto_register = false
auto_freeze = false
phase6_blocked = true
```

A human must separately decide whether to register a proposal through the Phase
5H.3 `register` command.

The frozen XRP 5G experiment is not read, modified, re-ranked, or re-registered
by Phase 5H.4.
