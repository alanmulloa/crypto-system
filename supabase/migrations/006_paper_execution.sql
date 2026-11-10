-- Phase 4B: durable paper-order authorization and idempotency.
-- No live broker credentials or exchange execution are introduced.

alter table if exists orders
  add column if not exists idempotency_key text,
  add column if not exists risk_snapshot jsonb not null default '{}'::jsonb;

create unique index if not exists orders_broker_idempotency_uidx
  on orders (broker, idempotency_key)
  where idempotency_key is not null;

alter table if exists fills
  add column if not exists realized_pnl_usd numeric not null default 0,
  add column if not exists raw jsonb not null default '{}'::jsonb;

create unique index if not exists fills_one_per_order_uidx
  on fills (order_id);

-- Existing RLS from migration 003 remains active.
