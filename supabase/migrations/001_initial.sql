create extension if not exists pgcrypto;

create table if not exists portfolio_positions (
  id uuid primary key default gen_random_uuid(),
  symbol text not null,
  quantity numeric not null default 0,
  avg_cost_usd numeric,
  capital_state text,
  source text,
  updated_at timestamptz not null default now()
);

create table if not exists opportunities (
  id uuid primary key default gen_random_uuid(),
  symbol text not null,
  strategy text not null,
  direction text not null,
  score numeric not null,
  confidence numeric not null,
  market_regime text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists decisions (
  id uuid primary key default gen_random_uuid(),
  opportunity_id uuid references opportunities(id),
  decision text not null,
  reasons jsonb not null default '[]'::jsonb,
  risk_approved boolean,
  max_notional_usd numeric,
  created_at timestamptz not null default now()
);

create table if not exists orders (
  id uuid primary key default gen_random_uuid(),
  decision_id uuid references decisions(id),
  broker text not null default 'PAPER',
  external_order_id text,
  symbol text not null,
  side text not null,
  order_type text not null,
  quantity numeric,
  notional_usd numeric,
  limit_price numeric,
  status text not null,
  raw jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists fills (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references orders(id),
  price numeric not null,
  quantity numeric not null,
  fee_usd numeric default 0,
  filled_at timestamptz not null default now()
);

create table if not exists trades (
  id uuid primary key default gen_random_uuid(),
  symbol text not null,
  strategy text,
  opened_at timestamptz,
  closed_at timestamptz,
  entry_price numeric,
  exit_price numeric,
  quantity numeric,
  pnl_usd numeric,
  pnl_pct numeric,
  market_regime text,
  metadata jsonb not null default '{}'::jsonb
);
