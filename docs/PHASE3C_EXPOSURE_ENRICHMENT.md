# Phase 3C - Exposure Enrichment and Daily Guards

## Why this phase exists

Phase 3A introduced portfolio-aware hard risk. Phase 3B synchronized the tracker into the agent.

Phase 3C tightens the data quality around two areas that should not be guessed:

1. custody/liquidity exposure;
2. daily risk counters.

## Custody concentration

The tracker often records a position with several reconciled sources, for example:

`Binance / Nexo / YouHodler`

That does not reveal how much value is held at each source.

The exposure analyzer therefore:

- attributes value only when exactly one custody source is known;
- keeps multi-source value in `multi_source_unattributed_usd`;
- keeps missing custody in `unknown_custody_usd`;
- never splits multi-source positions equally.

This avoids false concentration precision.

## Liquidity state

Internal states:

- LIQUID
- STAKED
- POOLED
- LOCKED
- UNKNOWN

The adapter prefers an explicit tracker field (`Estado liquidez` or `Liquidez`).

If absent, it may infer from `Tipo posición` only. The inference basis is stored so downstream risk code can distinguish explicit from inferred information.

It does not infer exact liquidity from platform name alone.

## Daily buy counter

The Apps Script bridge now reads `Operaciones ejecutadas` and sums today's rows where:

- Tipo = COMPRA
- Fecha ejecución is today in the spreadsheet timezone
- Ejecutado USD > 0

This value populates `daily_buy_used_usd`.

## Daily realized PnL

The current operation journal does **not** preserve enough realized cost-basis information to calculate daily realized PnL safely.

Therefore the bridge now exports:

`daily_realized_pnl_usd: null`

The portfolio Risk Manager treats an unavailable daily realized PnL as a hard block for new BUY approvals.

This is intentional: unknown loss status must not be interpreted as zero loss.

## What remains

Before Paper Trading can use a daily loss circuit breaker end-to-end, add an auditable realized-PnL ledger with:

- disposed quantity;
- allocated cost basis;
- proceeds;
- fees;
- realized PnL;
- timestamp;
- source operation/fill.

## Correlation / sector exposure

Not implemented in this phase.

The tracker does not currently provide reliable sector metadata and correlation should be calculated from historical return series rather than hardcoded labels. It belongs in a later evaluation/risk enrichment pass.

## Safety boundary

No execution capability is introduced.

- no broker;
- no Binance private API;
- no Futures/Margin;
- no withdrawals;
- no write-back from agent to tracker.
