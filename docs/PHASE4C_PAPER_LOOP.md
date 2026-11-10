# Phase 4C - Disabled-by-default Paper Loop

## Flow

`public market -> strategies -> aggregator -> paper portfolio overlay -> hard risk -> authorized paper orchestration -> PaperBroker`

The loop is disabled unless:

`PAPER_LOOP_ENABLED=true`

Default remains `false`.

## Paper portfolio overlay

Risk starts from the tracker portfolio context, then overlays the simulated paper account:

- paper cash replaces the cash-reserve value;
- paper asset quantities/values are added to existing holdings;
- daily paper BUY usage comes from paper fills;
- daily realized PnL comes from paper sell fills.

This means a second simulated cycle sees exposure created by the first cycle.

## Idempotent cycles

Every candidate order uses:

`paper-cycle:{cycle_id}:{symbol}`

Re-running the same cycle cannot create a second fill when the durable repository already contains the order.

## End-to-end guards covered by tests

- loop disabled by default;
- disabled loop does not even scan;
- kill switch blocks buys;
- WAIT/REJECT creates no order;
- Risk Manager caps notional;
- same cycle cannot double-fill;
- realized daily paper loss blocks the next BUY;
- subsequent cycles see previous paper exposure.

## Current scope

Paper BUY only.

There is still no automatic SELL/exit orchestration. Exit logic requires a dedicated risk contract so the system does not bypass spot-only disposal constraints.

## Not a daemon yet

Phase 4C defines the cycle, not scheduling or cloud hosting.

No recurring task is enabled by this code.

## No private exchange access

The entire loop still uses:

- public market data;
- local/Supabase paper state.

No Binance private endpoint or real key is used.

## Next step

Before moving to Binance Spot Testnet, Phase 5 should evaluate this paper system historically and prospectively:

- expectancy;
- drawdown;
- hit rate;
- profit factor;
- behavior by strategy/regime/timeframe;
- rejected-opportunity outcomes;
- out-of-sample stability.

The paper loop should run prospectively only after the Supabase migrations/configuration are deployed and explicitly enabled.
