-- Phase 3B one-way tracker -> agent sync journal.
-- Append-only and idempotent by content hash.

create table if not exists portfolio_syncs (
  id uuid primary key default gen_random_uuid(),
  schema_version text not null,
  source_id text not null,
  source_revision text not null,
  content_hash text not null unique,
  generated_at timestamptz not null,
  received_at timestamptz not null default now(),
  total_value_usd numeric not null,
  cash_value_usd numeric not null,
  capital_at_risk_usd numeric not null,
  snapshot jsonb not null default '{}'::jsonb,
  raw_payload jsonb not null default '{}'::jsonb
);

create index if not exists portfolio_syncs_source_generated_idx
  on portfolio_syncs (source_id, generated_at desc);

alter table if exists portfolio_syncs enable row level security;
