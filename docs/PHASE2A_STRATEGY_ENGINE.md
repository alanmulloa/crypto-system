# Phase 2A - Strategy Engine

## Scope

Phase 2A adds independent strategy hypotheses on top of Phase 1 Market Intelligence.

Implemented:

- Trend Following
- Pullback
- Breakout
- Mean Reversion
- Momentum
- normalized strategy contract
- deterministic score/confidence/reasons
- hypothetical entry/invalidation/stop/targets derived from ATR
- StrategyEngine that evaluates all strategies independently

Not implemented:

- no strategy aggregation into a final trade decision;
- no portfolio-aware sizing;
- no Risk Manager integration;
- no paper broker;
- no Binance private API;
- no orders.

## Contract

Every strategy returns a `StrategyAssessment`:

- symbol
- strategy
- state: WATCH / WAIT / REJECT
- direction hypothesis: BUY / SELL or none when rejected
- score
- confidence
- timeframe
- entry zone
- invalidation
- stop
- TP1 / TP2
- expected risk/reward
- reasons

A directional hypothesis is research output, not an executable order.

## Boundary

Dependency direction remains:

`market -> strategies -> future decision aggregation -> risk -> execution`

The Strategy Engine imports market contracts only. It does not import `risk` or `execution`.

The Phase 1 `ranking_score` is not used as strategy confidence or as an input to the strategies.

## Current heuristics

The initial rules are intentionally interpretable and deterministic. They are hypotheses to be tested, not claims of profitability.

- Trend: 4h/1d regime agreement plus structure/RSI/volume confirmation.
- Pullback: higher-timeframe trend plus 1h return toward EMA20.
- Breakout: directional 1h structure plus volume expansion, optionally confirmed by 4h.
- Mean reversion: 4h ranging regime plus stretched 1h RSI/price.
- Momentum: 1h EMA/RSI alignment plus volume, optionally confirmed by 4h.

## Next step - Phase 2B

Add a Strategy Aggregator that:

- compares strategy assessments without averaging incompatible setups blindly;
- detects contradictory BUY/SELL hypotheses;
- emits only WATCH / WAIT / REJECT at this stage;
- records evidence and conflict reasons;
- does not call risk or execution.

After that, Phase 2C must add historical sanity/backtest scaffolding with strict no-look-ahead behavior before Phase 3 portfolio/risk integration.
