# HANDOFF - Crypto System after Phase 3A

## Current state

Phase 1 Market Intelligence is hardened. Phase 2 implements five independent strategies, conflict-aware aggregation and historical no-look-ahead checks. Phase 3A adds an explicit portfolio contract and portfolio-aware hard risk evaluation.

The existing tracker remains the intended portfolio source of truth.

## Phase 3A behavior

The agent can consume tracker-shaped rows from:

- Cartera
- Asignación
- Conciliación histórica

and normalize them into an immutable `PortfolioSnapshot`.

It understands:

- current USD exposure;
- cash reserve;
- target/max asset weights;
- capital pending;
- SOLO GANANCIAS;
- capital at risk;
- reconstructed cost confidence context via tracker metadata;
- custody/source lists.

## Hard risk boundary

Strategies cannot change:

- kill switch;
- maximum notional per position;
- minimum cash reserve;
- maximum daily buy allocation;
- maximum open positions;
- daily loss limit;
- maximum allocation weight from the portfolio plan.

The Risk Manager is downstream of research strategies.

A research BUY is not an order.

A research SELL does not create a short. In Phase 3 it is only classified as a reduce/exit hypothesis and remains non-executable.

## Compatibility

The legacy `evaluate_risk()` API is retained. New portfolio-aware logic is exposed by `evaluate_portfolio_risk()`.

## New files

- `agent/app/portfolio/models.py`
- `agent/app/portfolio/tracker_contract.py`
- `agent/app/risk/portfolio.py`
- `agent/tests/test_portfolio.py`
- `agent/tests/test_portfolio_risk.py`
- `supabase/migrations/004_portfolio_risk.sql`
- `docs/PHASE3_PORTFOLIO_RISK.md`

## Still prohibited

- real trading;
- paper order execution;
- private Binance account/order calls;
- Futures;
- Margin;
- leverage;
- withdrawals;
- autonomous modification of hard risk settings.

## Next task - Phase 3B

Build a one-way synchronization path from the current tracker to the agent/Supabase while the tracker remains authoritative.

The sync must be idempotent, versioned and freshness-aware. It should not alter tracker portfolio values from the agent side.
