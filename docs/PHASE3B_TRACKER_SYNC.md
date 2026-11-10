# Phase 3B - One-way Tracker Sync

## Objective

Phase 3B creates a controlled, one-way synchronization path:

`Crypto Tracker -> Trading Agent -> Supabase`

The tracker remains authoritative during migration. The agent has no write-back path to Google Sheets.

## Payload

Schema version `1.0` contains:

- source id/revision;
- generation timestamp;
- Cartera rows;
- Asignación rows;
- Conciliación histórica rows;
- daily buy usage;
- daily realized PnL.

The agent canonicalizes the payload and calculates SHA-256. The hash is not trusted from the sender.

## Idempotency and freshness

Before persistence:

1. identical content hash -> DUPLICATE;
2. timestamp older/equal to the latest stored source snapshot -> STALE;
3. snapshot older than configured freshness window -> STALE;
4. timestamp too far in the future -> STALE;
5. otherwise -> APPLIED.

Only APPLIED snapshots are persisted.

## Security

The FastAPI endpoint is:

`POST /portfolio/sync`

It is disabled unless:

- `PORTFOLIO_SYNC_TOKEN` is configured;
- Supabase backend credentials are configured.

Authentication uses a Bearer token compared with constant-time comparison.

The token:

- is not committed to Git;
- is not exposed to the web UI;
- belongs in backend environment variables and Apps Script Script Properties.

Supabase RLS remains enabled.

## Tracker bridge

`PortfolioBridge.gs` adds:

- `previewPortfolioSyncV48()`
- `pushPortfolioSnapshotV48()`

Required Apps Script Script Properties:

- `CRYPTO_AGENT_SYNC_URL`
- `CRYPTO_AGENT_SYNC_TOKEN`

No agent function is able to alter Cartera, Asignación or Conciliación histórica.

## Current limitation

`daily_buy_used_usd` and `daily_realized_pnl_usd` are exported as zero by the initial bridge. They should be derived from `Operaciones ejecutadas` before Paper Trading or real daily-risk enforcement.

## Persistence model

Migration 005 creates append-only `portfolio_syncs` with:

- unique content hash;
- source revision;
- generated/received timestamps;
- portfolio summary;
- normalized snapshot JSON;
- original payload JSON.

This creates an auditable migration trail without overwriting historical snapshots.

## Next step

Phase 3C can enrich risk with custody concentration, staking/pool liquidity and broad correlation/sector exposure.

Before Paper Trading, implement daily metrics from actual operations and decide the long-term authority transition from tracker to Supabase.
