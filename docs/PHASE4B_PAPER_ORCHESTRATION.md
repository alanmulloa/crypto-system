# Phase 4B - Authorized Paper Orchestration

## Purpose

Phase 4B creates the safety boundary between risk decisions and the Paper Broker.

A strategy or aggregate assessment cannot directly create a paper order.

Flow:

`research -> PortfolioRiskDecision -> PaperExecutionIntent -> PaperExecutionOrchestrator -> PaperBroker`

## Authorization rules

The orchestrator requires:

- `risk.approved == true`;
- `risk.state == APPROVED`;
- risk symbol matches the execution intent;
- positive risk notional capacity.

The paper notional is always:

`min(requested_notional, risk.max_notional_usd)`

The caller cannot increase the Risk Manager authorization.

## Scope

Phase 4B currently creates paper BUY intents only.

This is intentional. Phase 3 does not yet authorize SELL/exit sizing, and the orchestration layer must not bypass that by calling the lower-level broker directly.

## Restart-safe idempotency

The repository is checked before the broker is called.

If an idempotency key already exists:

- exact same authorized intent returns the stored order;
- changed symbol/notional/type/limit raises an error;
- a fresh broker process cannot double-fill a persisted order.

This is stronger than in-memory idempotency alone.

## Persistence

Migration 006 adds:

- `orders.idempotency_key`;
- `orders.risk_snapshot`;
- unique `(broker, idempotency_key)`;
- `fills.realized_pnl_usd`;
- `fills.raw`;
- one fill per current Phase 4B order.

Supabase adapter uses backend service-role credentials only.

## Still deliberately absent

- no public execution endpoint;
- no scheduler;
- no automatic WATCH -> order conversion;
- no live/Testnet Binance client;
- no Futures/Margin;
- no withdrawals.

## Next step

Phase 4C can build an end-to-end **paper-only loop** that:

1. scans public market data;
2. evaluates strategies;
3. aggregates;
4. evaluates paper portfolio risk;
5. creates a paper execution intent only when approved;
6. persists the simulated result;
7. feeds paper realized PnL back into the next risk snapshot.

This loop must remain disabled by default until its tests demonstrate the daily-loss and kill-switch behavior end to end.
