# Phase 5H.12–5H.13 — Generic Signal + Public Prospective Runner

## 5H.12 Generic Signal Evaluator

The generic evaluator resolves the frozen registry definition directly against
signal-time `HistoricalPoint` data.

Supported research features are the exact features already used by Phase 5H.4:

- score / confidence
- RSI 15m / 1h / 4h
- ATR% 1h
- volume ratio 1h
- EMA distance 15m / 1h / 4h
- EMA spread 1h
- market structure 1h / 4h

The evaluator first requires the frozen symbol, strategy, WATCH state and
direction to match, then evaluates the registered operator and threshold.

## 5H.13 Public Prospective Runner

The runner reuses:

- `BinancePublicClient`
- `HistoricalSanityRunner`
- the 5H.10 frozen protocol
- the 5H.10 generic report integrity contract

The CLI downloads public Spot candles only and uses no credentials.

```bash
python -m app.evaluation.generic_prospective_runner_cli \
  --bootstrap reports/prospective/<experiment-id>/bootstrap.json \
  --output reports/prospective/<experiment-id>/fresh.json
```

Pre-freeze candles are fetched only to build signal-time lookback. The report
drops every signal at or before `frozen_at_ms`; only later signals can become
prospective observations.

The existing XRP Phase 5G collector is not migrated or modified.
