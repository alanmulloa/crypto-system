# Roadmap

## Phase 0 - Foundation ✅
## Phase 1 - Market Intelligence ✅
## Phase 2 - Strategies ✅
## Phase 3 - Portfolio + Risk ✅

## Phase 4 - Paper Trading

### Phase 4A - Paper Broker core ✅
- deterministic MARKET/LIMIT simulation
- fees/slippage
- positions/cost basis/realized PnL
- in-memory idempotency

### Phase 4B - Authorized paper orchestration ✅
- explicit approved RiskDecision required
- authorized notional capped by risk
- paper BUY intents only
- durable idempotency before broker call
- Supabase orders/fills persistence
- risk snapshot on order
- no execution API/live broker

### Phase 4C - Paper loop
- public market scan
- strategies + aggregation
- paper portfolio snapshot
- hard risk evaluation
- authorized paper order only
- realized-PnL feedback
- kill switch / daily-loss end-to-end tests
- monitoring

## Phase 5 - Backtesting + Evaluation
## Phase 6 - Binance Spot Testnet
## Phase 7 - External Signals
## Phase 8 - Dashboard Integration
## Phase 9 - Auto Limited
