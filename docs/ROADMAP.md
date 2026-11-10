# Roadmap

## Phase 0 - Foundation ✅

## Phase 1 - Market Intelligence ✅

## Phase 2 - Strategies ✅
- five strategies
- conflict-aware aggregation
- no-look-ahead historical sanity

## Phase 3 - Portfolio + Risk ✅
- tracker portfolio contract
- hard risk
- one-way sync
- exposure diagnostics
- daily-buy counter
- unknown realized-PnL safety block

## Phase 4 - Paper Trading

### Phase 4A - Paper Broker core ✅
- MARKET/LIMIT simulation
- deterministic fees/slippage
- cash and positions
- average cost
- realized PnL
- order lifecycle
- idempotency
- no network/private API

### Phase 4B - Authorized paper orchestration
- research -> risk -> paper authorization
- construct orders only from approved risk decisions
- persistence to orders/fills/trades
- restart-safe idempotency
- paper portfolio snapshots

### Phase 4C - Paper loop
- scheduled market scan
- strategy + aggregation
- risk evaluation
- approved paper orders only
- daily loss circuit breaker from paper realized PnL
- monitoring/metrics

## Phase 5 - Backtesting + Evaluation
- PnL/expectancy/profit factor/drawdown
- validation/out-of-sample
- correlation analytics

## Phase 6 - Binance Spot Testnet
- signed API
- filters/reconciliation
- manual approval

## Phase 7 - External Signals
- independent validation

## Phase 8 - Dashboard Integration

## Phase 9 - Auto Limited
Only after evidence:
- allow-list
- fixed hard-risk envelope
- circuit breakers
- no withdrawals/leverage
