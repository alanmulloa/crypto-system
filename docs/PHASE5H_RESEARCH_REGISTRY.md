# Phase 5H — Research Experiment Registry

## Purpose

Phase 5H provides research infrastructure for future candidate experiments without
mixing their definitions, lifecycle, or artifacts with the frozen XRP Phase 5G
prospective experiment.

It is passive infrastructure only. It does not fetch market data, run strategies,
place orders, use private Binance APIs, or authorize Phase 6.

## Registry

The canonical registry is:

```text
agent/research/experiment-registry.json
```

From the `agent/` directory:

```bash
python -m app.evaluation.experiment_registry_cli list
python -m app.evaluation.experiment_registry_cli show phase5g-xrp-low-volume-1h
python -m app.evaluation.experiment_registry_cli --json show phase5g-xrp-low-volume-1h
```

Each entry records:

- experiment id;
- symbol, strategy and direction;
- feature, operator and threshold;
- calibration and validation period metadata when canonically known;
- frozen timestamp in milliseconds;
- outcome horizon;
- fee/slippage assumptions;
- lifecycle status and current decision;
- artifact path.

The permitted lifecycle states are:

```text
DRAFT
CALIBRATION
VALIDATION
REJECTED
FROZEN
PROSPECTIVE
COMPLETE
```

Allowed transitions are deliberately narrow:

```text
DRAFT -> CALIBRATION | REJECTED
CALIBRATION -> VALIDATION | REJECTED
VALIDATION -> FROZEN | REJECTED
FROZEN -> PROSPECTIVE | REJECTED
PROSPECTIVE -> COMPLETE | REJECTED
```

`REJECTED` and `COMPLETE` are terminal.

## Frozen definition

Once an experiment is already `FROZEN`, `PROSPECTIVE`, or `COMPLETE`,
these definition fields cannot change during a lifecycle transition:

- symbol;
- strategy;
- direction;
- feature;
- operator;
- threshold;
- calibration period;
- validation period;
- freeze timestamp;
- outcome hours;
- fee bps;
- slippage bps.

This protects future research from silently changing the experiment after it has
been frozen.

## XRP Phase 5G bootstrap

The registry contains one bootstrap entry representing the already-existing 5G
experiment:

```text
id = phase5g-xrp-low-volume-1h
symbol = XRPUSDT
strategy = mean_reversion
direction = BUY
feature = volume_ratio_1h
operator = <=
threshold = 0.75
freeze_at_ms = 1794348615195
outcome_hours = 24
fee_bps = 10
slippage_bps = 5
status = PROSPECTIVE
artifact_path = reports/phase5g/
```

This entry is metadata only. Phase 5H does not recalculate or modify Phase 5G.
The existing Phase 5G artifacts do not expose canonical calibration/validation
period strings, so both registry fields are intentionally `null` rather than
invented.

## Security boundary

Phase 6 remains blocked. The registry does not add Testnet execution, live
execution, Futures, Margin, leverage, withdrawals, API keys, or any order path.
