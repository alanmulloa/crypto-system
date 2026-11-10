-- Security hardening before Phase 2.
-- Supabase service-role access continues to work because service-role bypasses RLS.
-- No anon/authenticated policies are created here, so browser/public clients cannot
-- read or mutate trading state directly.

alter table if exists portfolio_positions enable row level security;
alter table if exists opportunities enable row level security;
alter table if exists decisions enable row level security;
alter table if exists orders enable row level security;
alter table if exists fills enable row level security;
alter table if exists trades enable row level security;
alter table if exists market_candidates enable row level security;
