# Phase 5G - Frozen XRP Prospective Evidence Harness

## Frozen candidate

Phase 5F.2 selected one primary candidate for prospective observation:

```text
symbol = XRPUSDT
strategy = mean_reversion
direction = BUY
volume_ratio_1h <= 0.75
```

The candidate is frozen at:

```text
2026-11-10T22:10:15.195720+00:00
```

This timestamp is the creation time of the reviewed Phase 5F.2 artifact.

## Prospective boundary

Only Mean Reversion WATCH BUY signals with a signal timestamp strictly after the
frozen cutoff can enter the prospective sample.

The CLI may download up to 90 days before the cutoff only to provide indicator
lookback. Those pre-freeze candles cannot become observations.

Each prospective observation uses the same entry-range rule and a fixed 24h
outcome. Until enough future data exists, the observation remains `PENDING`.

## Cohorts

The report compares:

- baseline: every eligible XRPUSDT Mean Reversion WATCH BUY after the cutoff;
- candidate: the subset with `volume_ratio_1h <= 0.75`.

For matured observations it reports average/median net return and positive-return
rate. Costs remain 10 bps fee + 5 bps slippage.

`sample_ready` becomes true only after 20 matured candidate observations. It is
not an approval or promotion rule.

## Run

From `agent/`:

```bash
SSL_CERT_FILE="$(python -m certifi)" \
python -m app.evaluation.prospective_candidate_cli \
  --output reports/phase5g-xrp-prospective.json
```

Rerunning the command later is safe: the prospective cutoff remains fixed.

## Security boundary

The harness:

- uses public Binance market endpoints only;
- has no API keys;
- places no orders;
- does not use Testnet;
- does not modify hard risk;
- does not modify `mean_reversion.py`;
- does not authorize Phase 6.
