# Phase 5F - Strategy Diagnostics & Exit Research

## Purpose

Phase 5F is a research-only diagnostic layer for understanding why WATCH signals can
show favorable directional outcomes while the executable backtest remains negative.

The initial focus is `mean_reversion`.

This phase does **not** change strategy generation rules, hard risk limits, the tracker,
paper execution, or exchange execution.

## Methodology

For each WATCH BUY assessment, the diagnostic runner:

1. uses the first 1h candle strictly after the signal;
2. optionally requires that candle open to remain inside the strategy entry range;
3. applies the same default fee/slippage assumptions used by Phase 5D;
4. reconstructs only candles available after the signal;
5. bounds every temporal segment at that segment end;
6. never converts SELL hypotheses into shorts.

Default assumptions:

- fee: 10 bps;
- slippage: 5 bps;
- notional: USD 100;
- current exit horizon: 24h;
- research path horizon: 48h.

## Path diagnostics

Each analyzable BUY signal records:

- symbol and strategy;
- temporal segment;
- signal and entry timestamps;
- execution-adjusted entry price;
- market regime;
- score and confidence;
- 1h ATR;
- configured stop / TP1;
- current exit reason / timestamp / return;
- MFE / MAE;
- time to MFE / MAE;
- conservative intrabar ambiguity;
- favorable-then-loss flag;
- stop-before-later-recovery flag.

Directional snapshots are produced when enough future candles exist for:

- 1h;
- 2h;
- 4h;
- 8h;
- 12h;
- 24h;
- 48h.

Missing horizons are omitted rather than fabricated.

## Distributions

The report summarizes MFE, MAE and timing using:

- mean;
- p25;
- p50;
- p75;
- p90.

Horizon returns include:

- observation count;
- average net return;
- median net return;
- positive-return rate;
- average raw return.

Breakdowns are available by strategy, symbol, regime and temporal segment.

## Current exit analysis

The current configured exit is analyzed without changing its behavior.

The main backtest rule remains:

> if STOP and TP1 are touched in the same OHLC candle, STOP wins.

Phase 5F also counts such cases as `intrabar_ambiguous`.

It reports:

- STOP / TP1 / HORIZON counts and shares;
- expectancy and win rate by exit reason;
- MFE / MAE by exit reason;
- favorable excursion followed by a final loss;
- stop followed by later favorable recovery inside the research path.

## Exit research

Phase 5F compares predetermined scenarios only.

Fixed horizon exits:

- 4h;
- 8h;
- 12h;
- 24h;
- 48h.

ATR sensitivity:

Stops:

- 0.75 ATR;
- 1.0 ATR;
- 1.25 ATR;
- 1.5 ATR;
- 2.0 ATR.

Targets:

- 0.75 ATR;
- 1.0 ATR;
- 1.5 ATR;
- 2.0 ATR;
- 3.0 ATR.

ATR is read from the 1h `HistoricalPoint` analysis.

The ATR grid is sensitivity research, not automatic optimization.

## Critical OOS treatment

The Phase 5D OOS period has already been observed.

Therefore:

- it may be described;
- it must not be used to select parameters and then be called OOS again;
- ATR rows for OOS are explicitly marked `research_eligible=false`;
- parameter research should use calibration / validation only;
- any selected experimental configuration needs genuinely unseen future data or
  prospective evaluation before it can be called validated.

## CLI

From `agent/`:

```bash
python -m app.evaluation.diagnostics_cli \
  --days 730 \
  --symbols BTCUSDT ETHUSDT BNBUSDT SOLUSDT XRPUSDT \
  --strategy mean_reversion \
  --max-points 8000 \
  --output reports/phase5f-mean-reversion.json
```

The CLI uses only public Binance market data and requires no exchange credentials.

By default it stores at most 25 individual path examples per symbol/segment while
keeping all aggregate statistics. Use `--include-all-paths` only when full detail is
required.

## Interpretation

Phase 5F does not promote a strategy automatically.

It is intended to answer:

- how long the favorable move usually takes;
- how much adverse excursion happens first;
- whether current stops appear too tight;
- whether TP1 or 24h horizon appear poorly matched;
- whether costs consume an otherwise positive raw edge;
- whether behavior differs materially by asset or regime.

A positive diagnostic result is not approval for Testnet.

## Security and execution boundary

Phase 5F adds:

- no Testnet;
- no real orders;
- no private Binance API;
- no API keys;
- no Futures;
- no Margin;
- no leverage;
- no withdrawals.

## Next decision

After running and reviewing the diagnostic report:

1. reject the hypothesis, or
2. define one narrowly scoped experimental strategy/exit variant for a future phase.

Any experimental variant must be validated on new unseen data before Phase 6 is
considered.
