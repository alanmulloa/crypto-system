# HANDOFF - Crypto System after Phase 4C

## Current state

Phases 1-4 are implemented.

The system now contains an end-to-end paper-only cycle from public market candidates through strategies, aggregation, portfolio-aware risk and the deterministic Paper Broker.

## Disabled by default

`PAPER_LOOP_ENABLED=false`

A code deploy does not start trading or paper cycles automatically.

There is no scheduler/daemon in Phase 4C.

## Hard boundaries

- public market data only;
- no private Binance APIs;
- no Futures/Margin/leverage;
- no withdrawals;
- no real trading;
- paper BUYs require approved PortfolioRiskDecision;
- kill switch is downstream of strategy output;
- daily realized paper loss is fed into the next risk check;
- repeat cycle ids are idempotent.

## Exposure feedback

Paper positions are overlaid onto the tracker portfolio context before each risk decision, so simulated purchases affect subsequent max-weight/open-position/cash checks.

## Next task - Phase 5

Build evaluation around paper/historical outcomes before introducing any Testnet credentials.

Do not move to Testnet merely because paper execution works mechanically. Require measurable evidence and out-of-sample checks first.
