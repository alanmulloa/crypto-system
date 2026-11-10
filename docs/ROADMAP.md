# Roadmap

## Phase 0 - Foundation ✅

## Phase 1 - Market Intelligence ✅
- public Binance Spot data
- closed candles
- scanner/regime/indicators

## Phase 2 - Strategies ✅
- five strategies
- conflict-aware aggregation
- historical no-look-ahead sanity

## Phase 3 - Portfolio + Risk

### Phase 3A - Portfolio contract + hard risk ✅
- tracker-shaped portfolio
- capital states
- allocation/reserve-aware sizing
- hard limits

### Phase 3B - Tracker synchronization ✅
- one-way tracker -> agent/Supabase
- idempotent/versioned/freshness-aware
- append-only journal

### Phase 3C - Exposure enrichment + daily guards ✅
- custody exposure without false multi-source splitting
- LIQUID/STAKED/POOLED/LOCKED/UNKNOWN states
- explicit vs inferred liquidity basis
- daily buy counter from executed operations
- unknown realized PnL blocks BUY approval
- no fake zero-loss assumption

### Deferred risk enrichment
- realized-PnL ledger
- correlation from historical returns
- sector/category metadata
- destination-custody-aware concentration limits

## Phase 4 - Paper Trading
- paper broker
- fees/slippage
- order lifecycle
- fills
- realized-PnL ledger
- positions/trade journal
- idempotency

## Phase 5 - Backtesting + Evaluation
- PnL/expectancy/profit factor/drawdown
- calibration/validation/out-of-sample
- correlation/risk analytics

## Phase 6 - Binance Spot Testnet
- signed API
- exchange filters
- reconciliation
- manual approval mode

## Phase 7 - External Signals
- independent validation

## Phase 8 - Dashboard Integration
- expose agent state
- progressive source-of-truth migration

## Phase 9 - Auto Limited
Only after evidence:
- allow-list
- fixed hard-risk envelope
- loss/drawdown circuit breakers
- kill switch outside agent control
- no withdrawals/leverage
