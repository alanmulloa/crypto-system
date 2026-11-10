-- Phase 5C research-only temporal validation persistence.
-- Stores diagnostics; it does not enable Testnet or execution.

create table if not exists validation_runs (
  id uuid primary key default gen_random_uuid(),
  strategy text not null,
  split_config jsonb not null default '{}'::jsonb,
  calibration jsonb not null default '{}'::jsonb,
  validation jsonb not null default '{}'::jsonb,
  out_of_sample jsonb not null default '{}'::jsonb,
  stability jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists validation_runs_strategy_created_idx
  on validation_runs (strategy, created_at desc);

alter table if exists validation_runs enable row level security;
