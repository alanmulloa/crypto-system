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
- closed 15m / 1h / 4h / 1d candles
- universe/liquidity filters
- EMA / RSI / ATR / volume / structure
- market regime
- candidate ranking
- retry/backoff and partial-failure tolerance
- no execution

## Phase 2 - Strategies ✅

### Phase 2A - Independent Strategy Engine ✅
- trend following
- pullback
- breakout
- mean reversion
- momentum
- normalized WATCH / WAIT / REJECT assessments

### Phase 2B - Strategy Aggregator ✅
- separate BUY and SELL evidence
- explicit conflicts
- global WATCH / WAIT / REJECT
- no execution

### Phase 2C - Historical sanity ✅
- walk-forward historical runner
- per-timestamp timeframe truncation
- strict no-look-ahead regression
- deterministic output regression
- strategy/aggregate state diagnostics
- no profitability optimization

## Phase 3 - Portfolio + Risk

- consume current tracker portfolio
- map current custody and capital states
- allocation/exposure
- correlation/sector exposure
- position sizing
- max daily allocation/loss
- hard limits independent of strategy
- research decision -> risk decision contract

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
- train/calibration vs validation vs out-of-sample
- rejected-signal evaluation
- metrics by asset/regime/timeframe
- strategy calibration

## Phase 6 - Binance Spot Testnet

- signed API
- exchange filters
- idempotency
- reconciliation
- manual approval mode

## Phase 7 - External Signals

- external/copy adapters
- independent validation
- never blind-copy

## Phase 8 - Dashboard Integration

- expose agent state to current dashboard
- migrate tracker reads to Supabase incrementally
- preserve historical reconstruction

## Phase 9 - Auto Limited

Only after paper/Testnet evidence:

- allow-listed symbols only
- fixed hard-risk envelope
- daily loss stop
- drawdown circuit breaker
- kill switch outside agent control
- no withdrawals
- no leverage
