-- Phase 5A: immutable future-outcome labels for research evaluation.
-- No orders or execution capability are introduced.

create table if not exists outcome_observations (
  id uuid primary key default gen_random_uuid(),
  symbol text not null,
  source text not null check (source in ('aggregate', 'strategy')),
  strategy text,
  state text not null,
  direction text,
  score numeric not null,
  confidence numeric not null,
  signal_timestamp timestamptz not null,
  entry_price numeric not null,
  market_regime text,
  horizon text not null,
  target_timestamp timestamptz not null,
  observed_timestamp timestamptz not null,
  exit_price numeric not null,
  raw_return_pct numeric not null,
  max_up_pct numeric not null,
  max_down_pct numeric not null,
  directional_return_pct numeric,
  mfe_pct numeric,
  mae_pct numeric,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create unique index if not exists outcome_observations_identity_uidx
  on outcome_observations (
    symbol,
    source,
    coalesce(strategy, ''),
    signal_timestamp,
    horizon
  );

create index if not exists outcome_observations_lookup_idx
  on outcome_observations (symbol, source, strategy, state, horizon, signal_timestamp);

alter table if exists outcome_observations enable row level security;
