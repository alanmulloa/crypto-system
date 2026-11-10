# Phase 5F.2 - Mean Reversion Candidate Experiment

## Purpose

Phase 5F.2 turns the strongest Phase 5F.1 observations into explicit,
research-only candidate comparisons.

It does not modify `mean_reversion.py`, portfolio risk, paper execution, or
exchange integration.

## Predetermined candidates

### Primary

`XRPUSDT` Mean Reversion WATCH BUY with:

```text
volume_ratio_1h <= 0.75
```

### Secondary comparator

`ETHUSDT` Mean Reversion WATCH BUY with:

```text
structure_4h == lower_highs_lower_lows
```

These conditions are fixed before running Phase 5F.2. The experiment does not
search for new thresholds.

## Metrics

For calibration, validation, and descriptive OOS, each candidate reports:

- baseline observation count;
- candidate observation count;
- candidate coverage;
- baseline average 24h net return;
- candidate average 24h net return;
- candidate median 24h net return;
- positive-return rate;
- uplift versus the unchanged Mean Reversion baseline.

A candidate is eligible for a future prospective test only when calibration and
validation both have sufficient sample, positive average return, and positive
uplift.

The already-observed OOS segment cannot change this flag.

## Run

From `agent/`:

```bash
SSL_CERT_FILE="$(python -m certifi)" \
python -m app.evaluation.candidate_experiment_cli \
  --days 730 \
  --symbols XRPUSDT ETHUSDT \
  --max-points 8000 \
  --outcome-hours 24 \
  --min-observations 20 \
  --output reports/phase5f2-entry-candidates.json
```

## Promotion boundary

Passing Phase 5F.2 does not authorize Phase 6.

It only justifies freezing one research candidate for genuinely unseen future or
prospective paper evidence.

No existing OOS data may be relabeled as unseen validation.
