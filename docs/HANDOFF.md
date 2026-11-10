# HANDOFF - Crypto System after Phase 1 audit

## Current state

Phase 0 foundation is preserved and Phase 1 Market Intelligence is implemented. A Codex audit/hardening pass was performed before Phase 2. The tracker remains under `tracker/apps-script/crypto_tracker_v4_7_1_full/` and has not been functionally replaced.

The agent can use Binance public Spot endpoints without API keys to:

- read exchange metadata;
- read 24h tickers;
- download 15m, 1h, 4h and 1d candles;
- expose only fully closed candles to analysis;
- filter liquid USDT Spot markets;
- exclude known stablecoin bases, leveraged-token suffixes and selected wrapped duplicates;
- reject insufficient history;
- compute EMA, RSI, ATR, volume ratio and simple market structure;
- classify market regime;
- rank research candidates;
- tolerate a transient per-symbol failure without aborting the full scan.

It cannot generate BUY/SELL strategy signals or place orders.

## Audit hardening

See `docs/CODEX_AUDIT_PHASE1.md`.

Important fixes:

- incomplete/current Binance candles are discarded;
- transient public API failures use bounded retry/backoff;
- one failed symbol no longer aborts the entire scan;
- flat-price RSI is neutral (50), not 100;
- stablecoin exclusion includes USD1/USDS/RLUSD/EURI;
- Supabase RLS is enabled for all current public-schema tables by migration 003.

## Security invariants

Do not weaken these:

- no real trading;
- no Futures/Margin/leverage;
- no withdrawals;
- no private Binance endpoints in Phase 1;
- no API key needed for scanner;
- `KILL_SWITCH=true` default;
- risk limits remain operator configuration;
- service-role Supabase key is backend-only;
- public market source is independent from future execution/Testnet configuration;
- no anon/authenticated Supabase policies for trading state unless explicitly designed and reviewed.

## Important files

- `agent/app/market/binance_public.py`
- `agent/app/market/indicators.py`
- `agent/app/market/regime.py`
- `agent/app/market/scanner.py`
- `agent/app/market/service.py`
- `agent/app/market/cli.py`
- `agent/app/storage/market_repository.py`
- `supabase/migrations/002_market_intelligence.sql`
- `supabase/migrations/003_enable_rls.sql`
- `docs/CODEX_AUDIT_PHASE1.md`

## Validation

Before the audit, GitHub Actions on `main` passed `ruff check app tests` and `pytest -q`.

The audit adds regression tests for closed-candle filtering, retry behavior, flat RSI, stablecoin exclusion and partial scanner failure. Merge only if the audit PR CI is green.

## Open technical debt

Not blockers for Phase 2, but required before later autonomous execution:

- market observation idempotency and retention;
- order-book spread/depth filter;
- request-budget monitoring, caching and optional bounded concurrency;
- metadata-driven stablecoin/wrapped classification;
- payload/schema versioning;
- historical validation of regime thresholds.

## Next task - Phase 2

Implement a normalized strategy interface for trend following, pullback, breakout, mean reversion and momentum. Strategies may consume MarketCandidate/TimeframeAnalysis but must not access brokers or private APIs. Strategy outputs need score, confidence, direction hypothesis, entry/invalidation context and explicit reasons.

Do not implement order execution. Do not reuse `ranking_score` as strategy confidence. Before merging Phase 2, run historical sanity checks proving indicators and strategies only use information available at each timestamp.
