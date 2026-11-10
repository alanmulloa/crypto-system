# Roadmap

## Phase 0 - Foundation ✅
## Phase 1 - Market Intelligence ✅
## Phase 2 - Strategies ✅
## Phase 3 - Portfolio + Risk ✅
## Phase 4 - Paper Trading ✅

## Phase 5 - Backtesting + Evaluation

### Phase 5A - Outcome Evaluation ✅
### Phase 5B - Deterministic Spot Backtest ✅
### Phase 5C - Temporal Validation ✅

### Phase 5D - Real historical evidence tooling ✅
- paginated public Binance klines
- 15m / 1h / 4h / 1d
- closed-candle filtering
- deduplication
- gap diagnostics
- historical/live 250-candle parity
- multi-asset evidence runner
- JSON evidence artifact
- no credentials or execution

### Phase 5E - Evidence review ✅
- real 730-day evidence reviewed
- all five current strategy backtests negative in aggregate OOS
- mean_reversion WATCH outcomes identified as the primary research lead
- no approval for Testnet

### Phase 5F - Strategy diagnostics & exit research ✅
- path-level MFE / MAE and timing
- current-exit diagnostics
- fixed-horizon comparison
- predetermined ATR stop/target sensitivity
- symbol / regime / temporal-segment breakdowns
- observed OOS treated as descriptive only
- no strategy rule changes
- no Testnet or execution
- review conclusion: no stable exit-only variant justified
- Phase 5G deferred pending entry-quality evidence

### Phase 5F.1 - Mean Reversion entry-quality diagnostics ✅
- signal-time features only
- fixed score / confidence bands
- 1h RSI, ATR%, volume and EMA-distance context
- 15m and 4h alignment context
- 1h EMA20/EMA50 spread
- symbol and market-structure breakdowns
- repeated WATCH BUY clustering / cooldown evidence
- per-symbol and pooled five-symbol reports
- calibration + validation only for candidate screening
- previously observed OOS remains descriptive only
- real 730-day run reviewed
- no pooled bucket has positive return in both calibration and validation
- XRPUSDT volume_ratio_1h <= 0.75 is the strongest asset-specific research lead
- ETHUSDT 4h lower-highs/lower-lows is a weaker secondary lead

### Phase 5F.2 - Mean Reversion candidate experiment ✅
- predetermined XRPUSDT low-1h-volume candidate
- ETHUSDT 4h lower-highs/lower-lows comparator
- baseline vs candidate metrics by temporal segment
- calibration + validation determine eligibility
- XRP candidate passed the predefined research screen
- ETH comparator passed mechanically but with weak validation uplift
- observed OOS remains descriptive only
- no production strategy changes
- no Testnet or execution

### Phase 5G - Frozen XRP prospective evidence 🔬
- frozen candidate: XRPUSDT Mean Reversion WATCH BUY with volume_ratio_1h <= 0.75
- freeze cutoff: 2026-11-10T22:10:15.195720+00:00
- only post-freeze signals count as prospective observations
- pre-freeze history may be used only for indicator lookback
- baseline XRP cohort vs candidate subset
- 24h fixed outcome with existing fee/slippage assumptions
- pending vs matured observations
- no automatic promotion rule
- no Testnet or execution

### Phase 6 - Binance Spot Testnet
- still deferred until genuinely unseen prospective evidence supports progression

## Phase 6 - Binance Spot Testnet
- only after new unseen evidence supports progression
- signed API
- exchange filters
- reconciliation
- manual approval mode

## Phase 7 - External Signals
## Phase 8 - Dashboard Integration
## Phase 9 - Auto Limited
