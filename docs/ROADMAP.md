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

### Phase 5F.1 - Mean Reversion entry-quality diagnostics
- inspect only features available at signal time
- score / confidence bands
- normalized volatility context
- oversold depth / distance from mean
- momentum and slope context
- multi-timeframe alignment
- symbol behavior
- repeated-signal clustering and cooldown candidates
- calibration + validation only for candidate selection
- previously observed OOS remains descriptive only

### Phase 5G - Experimental variant (deferred)
- define one narrow research variant only if 5F.1 supports it
- validate on genuinely unseen future data or prospective paper observations

## Phase 6 - Binance Spot Testnet
- only after new unseen evidence supports progression
- signed API
- exchange filters
- reconciliation
- manual approval mode

## Phase 7 - External Signals
## Phase 8 - Dashboard Integration
## Phase 9 - Auto Limited
