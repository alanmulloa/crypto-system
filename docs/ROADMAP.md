# Roadmap

## Phase 0 - Foundation ✅
- preserve tracker
- repo structure
- Supabase schema
- FastAPI skeleton
- hard risk config
- CI skeleton

## Phase 1 - Market Intelligence ✅
- public Binance Spot market data
- closed multi-timeframe candles
- market indicators/regime
- candidate scanner
- no execution

## Phase 2 - Strategies ✅

### Phase 2A - Independent Strategy Engine ✅
- trend
- pullback
- breakout
- mean reversion
- momentum

### Phase 2B - Strategy Aggregator ✅
- separate BUY/SELL evidence
- conflict handling
- WATCH / WAIT / REJECT

### Phase 2C - Historical sanity ✅
- walk-forward evaluator
- no-look-ahead regression
- deterministic diagnostics

## Phase 3 - Portfolio + Risk

### Phase 3A - Portfolio contract + hard risk ✅
- consume tracker-shaped portfolio data
- normalize capital states
- preserve SOLO GANANCIAS semantics
- allocation targets and max weights
- reserve-aware sizing
- daily buy/loss limits
- max open positions
- kill switch
- no shorts
- no execution

### Phase 3B - Tracker synchronization
- one-way tracker -> agent snapshot
- sync freshness/versioning
- idempotent Supabase persistence
- keep tracker authoritative during migration

### Phase 3C - Exposure enrichment
- custody concentration
- correlation/sector exposure
- staking/pool liquidity flags
- richer risk attribution

## Phase 4 - Paper Trading
- paper broker
- fees/slippage
- order lifecycle
- fills
- positions
- trade journal
- idempotency

## Phase 5 - Backtesting + Evaluation
- PnL/expectancy/profit factor/drawdown
- calibration/validation/out-of-sample
- rejected-signal evaluation

## Phase 6 - Binance Spot Testnet
- signed API
- exchange filters
- reconciliation
- manual approval mode

## Phase 7 - External Signals
- adapters
- independent validation
- never blind-copy

## Phase 8 - Dashboard Integration
- expose agent state
- migrate tracker reads progressively

## Phase 9 - Auto Limited
Only after paper/Testnet evidence:
- allow-listed symbols
- fixed hard-risk envelope
- daily loss stop
- circuit breakers
- kill switch outside agent control
- no withdrawals
- no leverage
