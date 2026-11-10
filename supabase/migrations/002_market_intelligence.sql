-- Phase 1: append-only market intelligence observations.
-- This table stores scanner output, not buy/sell signals.
create table if not exists market_candidates (
  id uuid primary key default gen_random_uuid(),
  symbol text not null,
  ranking_score numeric not null default 0,
  quote_volume_24h numeric not null default 0,
  payload jsonb not null default '{}'::jsonb,
  observed_at timestamptz not null default now()
);

create index if not exists idx_market_candidates_symbol_observed
  on market_candidates(symbol, observed_at desc);

create index if not exists idx_market_candidates_score_observed
  on market_candidates(ranking_score desc, observed_at desc);

-- No public policies are added here. Backend/service-role access only in Phase 1.
