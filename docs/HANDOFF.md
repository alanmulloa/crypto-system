# HANDOFF - Crypto System after Phase 4B

## Current state

Phases 1-3 are complete. Phase 4A provides a deterministic Paper Broker. Phase 4B adds the risk-gated orchestration and durable paper persistence boundary.

## Safety path

A strategy cannot call the broker directly through the orchestration path.

The required chain is:

`AggregatedAssessment -> PortfolioRiskDecision -> PaperExecutionIntent -> PaperExecutionOrchestrator -> PaperBroker`

Only an APPROVED risk decision can create a paper BUY.

The requested notional is capped by the Risk Manager authorization.

## Restart safety

Idempotency is checked in the repository before a broker call. This protects against process restarts creating a duplicate simulated fill.

## Persistence

Migration:

`supabase/migrations/006_paper_execution.sql`

adds durable idempotency/risk metadata to paper orders and realized PnL to fills.

## Still not active automatically

There is no scheduler and no execution API route.

Nothing in Phase 4B automatically converts a WATCH into an order.

No Binance private API exists.

## Next task - Phase 4C

Build a disabled-by-default end-to-end paper loop, including paper account state and realized-PnL feedback into hard risk.

The end-to-end tests must prove:

- kill switch stops the loop;
- daily loss stops new paper buys;
- duplicate cycles cannot double-fill;
- no WAIT/REJECT state creates an order;
- maximum notional cannot be exceeded.
