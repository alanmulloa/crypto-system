-- Phase 3 portfolio/risk shared-storage contract.
-- Does not create execution capability.

alter table if exists portfolio_positions
  add column if not exists market_value_usd numeric,
  add column if not exists capital_pending_usd numeric,
  add column if not exists custody jsonb not null default '[]'::jsonb,
  add column if not exists position_type text;

create table if not exists portfolio_allocations (
  id uuid primary key default gen_random_uuid(),
  asset text not null unique,
  target_weight_pct numeric,
  max_weight_pct numeric,
  priority text,
  updated_at timestamptz not null default now(),
  constraint portfolio_allocations_target_pct_ck
    check (target_weight_pct is null or (target_weight_pct >= 0 and target_weight_pct <= 100)),
  constraint portfolio_allocations_max_pct_ck
    check (max_weight_pct is null or (max_weight_pct >= 0 and max_weight_pct <= 100)),
  constraint portfolio_allocations_order_ck
    check (target_weight_pct is null or max_weight_pct is null or target_weight_pct <= max_weight_pct)
);

alter table if exists portfolio_allocations enable row level security;

create table if not exists portfolio_risk_snapshots (
  id uuid primary key default gen_random_uuid(),
  total_value_usd numeric not null,
  cash_value_usd numeric not null,
  capital_at_risk_usd numeric not null,
  open_positions integer not null,
  daily_buy_used_usd numeric not null default 0,
  daily_realized_pnl_usd numeric not null default 0,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

alter table if exists portfolio_risk_snapshots enable row level security;
