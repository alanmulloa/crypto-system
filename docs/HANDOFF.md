# HANDOFF - Crypto System after Phase 4A

## Current state

Phases 1-3 are complete. Phase 4A adds a deterministic in-memory Paper Broker.

It can simulate MARKET/LIMIT orders, cash, positions, fees, slippage and realized PnL.

It is **not connected** to strategies or real exchange APIs.

## Paper Broker boundary

`agent/app/execution/paper.py`

The class performs no network I/O.

There is no execution API route.

No Binance API key is read or used.

## Idempotency

Every paper order requires a unique idempotency key. Exact replay returns the original order; conflicting reuse raises.

## Accounting

- BUY fees enter average cost.
- SELL fees reduce net proceeds.
- realized PnL is recorded per fill.
- daily realized PnL can be queried from paper fills.

This gives the next phase a trustworthy daily-loss signal for the simulated account.

## Next task - Phase 4B

Add an orchestration boundary that accepts only an approved portfolio RiskDecision and turns it into a PaperOrderRequest.

Persist paper orders/fills/trades through repository interfaces backed by Supabase.

Do not add Binance private APIs yet.
