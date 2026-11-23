-- Phase 8Y/9F: AI Trading Cockpit - Bot Activity Trace
-- Adds missing links: decision_status, order→decision, fill→order, trade→order
-- Enables complete read model: Opportunity → Decision → Order → Fill → Trade

-- 1. Add decision_status to decisions (tracks lifecycle: PENDING/APPROVED/REJECTED/EXECUTED)
alter table if exists decisions
  add column if not exists decision_status text not null default 'PENDING'
  check (decision_status in ('PENDING', 'APPROVED', 'REJECTED', 'EXECUTED'));

create index if not exists idx_decisions_status_created
  on decisions (decision_status, created_at desc);

-- 2. Ensure orders.decision_id has proper index for join
create index if not exists idx_orders_decision_id
  on orders (decision_id);

-- 3. Ensure fills.order_id has proper index (already has unique index from 006)
-- but add explicit index for join performance
create index if not exists idx_fills_order_id
  on fills (order_id);

-- 4. Add order_id to trades to complete the trace chain
alter table if exists trades
  add column if not exists order_id uuid references orders(id);

create index if not exists idx_trades_order_id
  on trades (order_id);

-- 5. Add bot_run_id to group related activity (optional but useful for cockpits)
alter table if exists opportunities
  add column if not exists bot_run_id uuid;

create index if not exists idx_opportunities_bot_run
  on opportunities (bot_run_id);

-- 6. Add execution metadata to orders for richer cockpit display
alter table if exists orders
  add column if not exists execution_price numeric,
  add column if not exists execution_quantity numeric,
  add column if not exists execution_fee_usd numeric,
  add column if not exists execution_timestamp timestamptz;

-- 7. Add PnL tracking to trades (already has pnl_usd, pnl_pct but add realized_pnl for consistency)
alter table if exists trades
  add column if not exists realized_pnl_usd numeric default 0;

-- 8. Create a view for the complete bot activity trace (read-only for cockpit)
create or replace view bot_activity_trace as
select
  o.id as opportunity_id,
  o.symbol,
  o.strategy as opportunity_strategy,
  o.direction as opportunity_direction,
  o.score as opportunity_score,
  o.confidence as opportunity_confidence,
  o.created_at as opportunity_created_at,
  d.id as decision_id,
  d.decision as decision_action,
  d.decision_status,
  d.risk_approved,
  d.max_notional_usd,
  d.created_at as decision_created_at,
  ord.id as order_id,
  ord.symbol as order_symbol,
  ord.side as order_side,
  ord.order_type as order_type,
  ord.quantity as order_quantity,
  ord.notional_usd as order_notional_usd,
  ord.limit_price as order_limit_price,
  ord.status as order_status,
  ord.execution_price,
  ord.execution_quantity,
  ord.execution_fee_usd,
  ord.execution_timestamp,
  ord.created_at as order_created_at,
  f.id as fill_id,
  f.price as fill_price,
  f.quantity as fill_quantity,
  f.fee_usd as fill_fee_usd,
  f.realized_pnl_usd as fill_realized_pnl_usd,
  f.filled_at,
  t.id as trade_id,
  t.strategy as trade_strategy,
  t.opened_at,
  t.closed_at,
  t.entry_price,
  t.exit_price,
  t.quantity as trade_quantity,
  t.pnl_usd as trade_pnl_usd,
  t.pnl_pct as trade_pnl_pct,
  t.realized_pnl_usd as trade_realized_pnl_usd,
  t.market_regime as trade_market_regime
from opportunities o
left join decisions d on d.opportunity_id = o.id
left join orders ord on ord.decision_id = d.id
left join fills f on f.order_id = ord.id
left join trades t on t.order_id = ord.id
order by o.created_at desc;

-- RLS remains enabled from migration 003 - service-role bypasses for backend access