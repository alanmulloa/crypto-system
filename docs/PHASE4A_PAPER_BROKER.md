# Phase 4A - Paper Broker Core

## Scope

Phase 4A adds an in-memory deterministic Paper Broker.

It is a simulation primitive only. It is not wired to the strategy engine, Risk Manager, scheduler, API routes or Binance.

## Supported

- MARKET BUY/SELL;
- LIMIT BUY/SELL;
- deterministic slippage;
- configurable fees;
- cash balance;
- positions and average cost;
- realized PnL on sells;
- daily realized PnL;
- open/filled/rejected/cancelled lifecycle;
- idempotency keys;
- insufficient cash/position rejection.

## Cost basis

Paper BUY cost basis includes simulated fees.

Paper SELL realized PnL is:

`net proceeds after fee - disposed quantity x current paper average cost`

When a position is fully closed, quantity and average cost reset to zero.

## Slippage

For MARKET:

- BUY price = market x (1 + slippage);
- SELL price = market x (1 - slippage).

For LIMIT orders, simulated slippage is capped by the limit price so the broker never fills a BUY above its limit or a SELL below its limit.

## Idempotency

Every order requires an `idempotency_key`.

Submitting the exact same request with the same key returns the existing order without a second fill.

Reusing the key for a different request raises an error.

## Safety boundary

There is deliberately:

- no FastAPI execution endpoint;
- no Binance private API;
- no API key use;
- no network I/O;
- no automatic conversion of WATCH into an order.

Phase 4B should add a paper orchestration layer that requires an explicit RiskDecision authorization before constructing a PaperOrderRequest, plus persistence into the existing orders/fills/trades tables.

## Why this comes before Testnet

The system must prove order lifecycle, idempotency, accounting and realized PnL behavior locally before any signed exchange API is introduced.
