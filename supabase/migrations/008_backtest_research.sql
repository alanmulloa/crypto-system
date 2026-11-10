-- Phase 5B research-only backtest persistence.
-- No execution permissions or broker integrations.

create table if not exists backtest_runs (
  id uuid primary key default gen_random_uuid(),
  strategy text not null,
  config jsonb not null default '{}'::jsonb,
  initial_cash_usd numeric not null,
  ending_cash_usd numeric not null,
  net_pnl_usd numeric not null,
  expectancy_usd numeric,
  profit_factor numeric,
  win_rate_pct numeric,
  max_closed_equity_drawdown_pct numeric not null,
  trade_count integer not null,
  skipped jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists backtest_trades (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references backtest_runs(id) on delete cascade,
  symbol text not null,
  strategy text not null,
  direction text not null,
  signal_timestamp timestamptz not null,
  entry_timestamp timestamptz not null,
  exit_timestamp timestamptz not null,
  entry_price numeric not null,
  exit_price numeric not null,
  quantity numeric not null,
  entry_notional_usd numeric not null,
  entry_fee_usd numeric not null,
  exit_fee_usd numeric not null,
  pnl_usd numeric not null,
  return_pct numeric not null,
  mfe_pct numeric not null,
  mae_pct numeric not null,
  exit_reason text not null,
  market_regime text,
  created_at timestamptz not null default now()
);

create index if not exists backtest_trades_run_idx
  on backtest_trades (run_id, entry_timestamp);

alter table if exists backtest_runs enable row level security;
alter table if exists backtest_trades enable row level security;
