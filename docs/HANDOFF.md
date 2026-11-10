# HANDOFF - Crypto System after Phase 3B

## Current state

Market Intelligence, strategies, aggregation, no-look-ahead historical sanity, portfolio contracts and hard risk are implemented.

Phase 3B now provides a one-way, idempotent tracker synchronization path.

## Data authority

For now:

**Crypto Tracker remains authoritative for portfolio state.**

Flow:

`Tracker -> /portfolio/sync -> PortfolioSyncService -> Supabase portfolio_syncs`

There is deliberately no reverse flow.

## Sync safety

- versioned payload;
- server-calculated SHA-256;
- duplicate suppression;
- stale snapshot rejection;
- future-clock rejection;
- freshness window;
- append-only Supabase journal;
- RLS;
- bearer token stored outside Git.

## Tracker bridge

Source file:

`tracker/apps-script/crypto_tracker_v4_7_1_full/PortfolioBridge.gs`

Preview:

`previewPortfolioSyncV48()`

Push:

`pushPortfolioSnapshotV48()`

Script Properties required:

- CRYPTO_AGENT_SYNC_URL
- CRYPTO_AGENT_SYNC_TOKEN

Do not put the token in source code.

## Important limitation before Paper Trading

The first bridge exports:

- daily_buy_used_usd = 0
- daily_realized_pnl_usd = 0

These counters must be derived from Operaciones ejecutadas before relying on daily buy/loss enforcement in a live paper loop.

## Next task - Phase 3C

Add custody concentration and liquidity/staking/pool flags, then derive daily risk counters from the tracker operation journal.

Still prohibited:

- real orders;
- private Binance trading endpoints;
- Futures/Margin/leverage;
- withdrawals;
- agent write-back into tracker portfolio data.
