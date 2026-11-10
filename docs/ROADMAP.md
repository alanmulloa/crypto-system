# Roadmap

## Phase 0 - Foundation ✅

- preserve tracker
- repo structure
- Supabase schema
- FastAPI skeleton
- hard risk config
- CI skeleton

## Phase 1 - Market Intelligence ✅

- Binance public `exchangeInfo`
- public 24h tickers
- public klines
- 15m / 1h / 4h / 1d
- SPOT/TRADING/USDT filtering
- stablecoin, leveraged-token and wrapped-duplicate exclusions
- liquidity, volume and minimum-history filtering
- EMA / RSI / ATR / volume ratio / market structure
- bullish / bearish / ranging / high-volatility regimes
- multi-timeframe research-candidate ranking
- optional Supabase persistence without credentials required for tests
- mocked integration coverage
- no buy/sell signals

## Phase 2 - Strategies

- standard strategy contract
- trend following
- pullback
- breakout
- mean reversion
- momentum
- normalized scores and reasons
- conflict handling across strategies/timeframes
- decision output limited to research/watch/wait/reject until risk integration

## Phase 3 - Portfolio + Risk

- consume current tracker portfolio
- capital states (`SOLO GANANCIAS`, capital pending, pool/staking)
- allocation and exposure
- correlation/sector exposure
- position sizing
- hard limits independent of strategy

## Phase 4 - Paper Trading

- paper broker
- fees/slippage
- order lifecycle
- fills
- positions
- trade journal
- idempotency

## Phase 5 - Backtesting + Evaluation

- no look-ahead
- train/calibration vs validation vs out-of-sample
- rejected-signal evaluation
- strategy metrics by asset/regime/timeframe
- forecast calibration

## Phase 6 - Binance Spot Testnet

- signed API
- exchange filters (tick/step/min-notional)
- idempotency keys
- reconciliation
- explicit manual approval mode

## Phase 7 - External Signals

- adapters for external/copy signals
- independent validation
- never blind-copy

## Phase 8 - Dashboard Integration

- expose agent state to existing dashboard
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
