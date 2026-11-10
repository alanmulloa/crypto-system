# HANDOFF - Crypto System after Phase 2A

## Current state

Phase 1 Market Intelligence is hardened and Phase 2A adds an independent Strategy Engine. The existing tracker remains preserved.

The agent can:

- scan public Binance Spot market data;
- analyze closed candles only;
- classify regime and rank research candidates;
- evaluate five independent strategy hypotheses:
  - Trend Following
  - Pullback
  - Breakout
  - Mean Reversion
  - Momentum

It still cannot aggregate these hypotheses into a trade decision or place orders.

## Phase 2A invariants

- `ranking_score` is not strategy confidence.
- Strategies import market contracts only.
- Strategies do not import Risk Manager or execution modules.
- Strategy state is only WATCH / WAIT / REJECT.
- BUY/SELL is a hypothesis direction, not an order.
- A rejected assessment has no direction.
- Technical levels are hypothetical research levels derived deterministically from current closed-candle indicators.

## Important files

- `agent/app/strategies/base.py`
- `agent/app/strategies/common.py`
- `agent/app/strategies/trend.py`
- `agent/app/strategies/pullback.py`
- `agent/app/strategies/breakout.py`
- `agent/app/strategies/mean_reversion.py`
- `agent/app/strategies/momentum.py`
- `agent/app/strategies/engine.py`
- `agent/tests/test_strategies.py`
- `docs/PHASE2A_STRATEGY_ENGINE.md`

## Security invariants

Do not weaken:

- Spot only;
- no real trading;
- no private Binance endpoints;
- no Futures/Margin/leverage;
- no withdrawals;
- no broker calls from strategy code;
- hard risk limits remain outside strategy control;
- Supabase service role backend-only;
- RLS remains enabled.

## Open technical debt

From Phase 1:

- market observation idempotency/retention;
- order-book spread/depth;
- cache/request-budget monitoring;
- metadata-driven asset exclusions;
- regime threshold historical validation.

From Phase 2A:

- heuristic strategy thresholds require historical validation;
- technical entry/stop/target levels are generic ATR-based hypotheses;
- strategies currently consume indicator snapshots, not raw candle patterns;
- no conflict aggregator yet.

## Next task - Phase 2B

Build a Strategy Aggregator that consumes the five assessments and emits a single research state of WATCH / WAIT / REJECT with explicit conflict/evidence handling. It must not call Risk Manager or execution.

Then implement Phase 2C historical sanity checks before integrating portfolio/risk.
