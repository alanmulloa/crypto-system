# Roadmap

## Phase 0 - Foundation ✅

## Phase 1 - Market Intelligence ✅
- public Binance Spot market data
- closed multi-timeframe candles
- scanner/regime/indicators
- no execution

## Phase 2 - Strategies ✅
- five independent strategies
- conflict-aware aggregator
- historical no-look-ahead sanity

## Phase 3 - Portfolio + Risk

### Phase 3A - Portfolio contract + hard risk ✅
- tracker-shaped portfolio model
- capital-state normalization
- allocation/reserve-aware sizing
- hard risk boundaries
- no shorts/execution

### Phase 3B - Tracker synchronization ✅
- one-way tracker -> agent/Supabase
- versioned payload
- SHA-256 idempotency
- stale/future snapshot rejection
- append-only audit journal
- bearer-token protected endpoint
- no agent write-back to tracker

### Phase 3C - Exposure enrichment
- custody concentration
- staking/pool liquidity flags
- correlation/sector exposure
- richer risk attribution
- derive daily-risk counters from executed operations

## Phase 4 - Paper Trading
- paper broker
- fees/slippage
- lifecycle/fills/positions
- trade journal/idempotency

## Phase 5 - Backtesting + Evaluation
- PnL/expectancy/profit factor/drawdown
- calibration/validation/out-of-sample

## Phase 6 - Binance Spot Testnet
- signed API
- filters/reconciliation
- manual approval mode

## Phase 7 - External Signals
- independently validated adapters

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
