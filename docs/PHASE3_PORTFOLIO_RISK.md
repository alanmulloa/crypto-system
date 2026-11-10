# Phase 3 - Portfolio + Risk

## Goal

Phase 3 connects the strategy research layer to the existing Crypto Tracker portfolio model without creating a second source of truth.

The agent now has an explicit portfolio contract that can consume rows from:

- `Cartera`
- `Asignación`
- `Conciliación histórica`

No tracker data is hardcoded into the agent and the agent does not write back to the Google Sheet in this phase.

## Portfolio contract

`PortfolioSnapshot` contains:

- holdings by asset;
- quantity;
- current USD value;
- reconstructed average cost when available;
- capital pending;
- normalized capital state;
- custody/source list;
- position type;
- allocation targets;
- cash reserve;
- daily buy usage;
- daily realized PnL.

Capital-state normalization preserves tracker semantics such as:

- SOLO GANANCIAS -> PROFITS_ONLY
- CAPITAL EN RIESGO -> CAPITAL_AT_RISK
- CAPITAL RECUPERADO / REVISAR -> RECOVERED_REVIEW
- CAPITAL EN RIESGO - RECONSTRUCCION PARCIAL -> PARTIAL_RECONSTRUCTION
- USDC/Reserva -> CASH_RESERVE

`PROFITS_ONLY` is preserved as analytical metadata. It does **not** relax hard risk limits.

## Portfolio-aware Risk Manager

`evaluate_portfolio_risk()` consumes:

1. Phase 2B `AggregatedAssessment`;
2. `PortfolioSnapshot`;
3. immutable operator `Settings`.

A BUY hypothesis can only be approved when all hard constraints pass:

- aggregate state is WATCH;
- kill switch is off;
- max open positions is respected;
- daily loss stop is not reached;
- minimum cash reserve remains intact;
- daily buy limit remains;
- per-position hard USD maximum remains;
- tracker allocation max weight is not exceeded.

Maximum research notional is the minimum remaining capacity across those independent constraints.

## Spot-only SELL handling

Phase 3 does not open shorts.

A SELL research hypothesis:

- cannot create a position when the asset is not held;
- is treated only as a future reduce/exit hypothesis when the asset is held;
- is never approved for execution in Phase 3.

## Compatibility

The old `evaluate_risk()` interface remains unchanged for compatibility with Phase 0 tests and callers.

Phase 3 adds a separate portfolio-aware API rather than silently changing old behavior.

## Supabase

Migration `004_portfolio_risk.sql` extends shared storage with:

- current market value;
- capital pending;
- custody metadata;
- position type;
- allocation targets;
- optional portfolio-risk snapshots.

RLS remains enabled. No browser policies or execution permissions are added.

## Still not implemented

- direct Google Sheets ingestion/sync;
- live portfolio polling;
- real/Paper orders;
- sell sizing;
- correlation/sector exposure;
- fee/slippage modeling;
- PnL backtesting.

## Next step

Phase 3B should build the one-way tracker -> agent synchronization adapter, preferably through a controlled export/API or Supabase bridge, while keeping the tracker authoritative during migration.

After that, Phase 4 can introduce a Paper Broker.
