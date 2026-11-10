# Codex Audit - Phase 1 Market Intelligence

Audit date: 2026-11-10

Scope: Phase 0 foundation + Phase 1 Market Intelligence on `main`. No Phase 2 strategies or execution were added.

## Executive summary

Phase 1 has a sound separation between public market intelligence and future execution. No private Binance trading endpoints, Futures, Margin, withdrawals, or live-order code were found. The current architecture is suitable for Phase 2 after the hardening items in this audit are merged.

The audit found no CRITICAL issues. It found two HIGH issues that should be fixed before Phase 2: incomplete Binance candles could reach indicators/strategies and Supabase tables were created without RLS. Both are fixed in this audit branch.

## Findings

### CRITICAL

None found.

### HIGH

1. **Open Binance candle could be analyzed - FIXED**
   - `/api/v3/klines` can include the currently forming candle.
   - The previous client accepted every returned row.
   - That creates unstable indicators and a future look-ahead/repainting risk.
   - Fix: discard candles whose `close_time_ms` is later than the runtime clock; test added.

2. **Supabase public-schema tables had RLS disabled - FIXED**
   - Migrations created trading/portfolio tables in `public` but did not enable RLS.
   - "No policies" is not a security boundary when RLS itself is disabled.
   - Fix: migration `003_enable_rls.sql` enables RLS on all current tables and creates no browser policies. Backend service-role remains the intended Phase 1 access path.

### MEDIUM

1. **No retry/backoff for transient Binance failures - FIXED**
   - A single timeout/429/5xx could fail market-data acquisition.
   - Fix: bounded exponential retry for transient network errors, 418/429 and 5xx. Retry-After is honored when numeric.

2. **One symbol failure aborted the whole scan - FIXED**
   - A kline failure during one candidate propagated and stopped scanning.
   - Fix: Binance/data errors skip only that symbol and are logged.

3. **Flat RSI returned 100 instead of neutral 50 - FIXED**
   - When average gain and average loss were both zero, the old zero-loss branch returned 100.
   - Fix: return 50 for a flat series; regression test added.

4. **Stablecoin exclusion is static and incomplete - PARTIALLY FIXED**
   - Added USD1, USDS, RLUSD and EURI to the current exclusion set.
   - Remaining debt: replace static maintenance with a reviewed metadata/config source before broad autonomous scanning.

5. **Supabase market observations are not idempotent - OPEN**
   - Re-running a scan appends duplicate observations.
   - Before scheduled high-frequency scans, add a scan/observation key and retention policy.

6. **No order-book spread/depth filter - OPEN**
   - Quote volume + trade count are proxies, not execution-quality measures.
   - Should be added before paper execution or Testnet, not required for research candidate generation.

### LOW

1. REST acquisition is synchronous; bounded concurrency/caching can be added when scan cadence requires it.
2. Regime thresholds (RSI 52/48, ATR% 4.5) are heuristics and must be validated out-of-sample.
3. Market structure is intentionally simple and can misclassify noisy ranges.
4. No payload/schema version is stored with `market_candidates`; add before long-lived analytics migrations.
5. CI dependencies are exact-pinned but no lockfile/hash verification exists yet.

## Architecture

Strengths:

- Market data is independent from future execution/Testnet settings.
- Strategies do not exist yet, so Market Intelligence cannot place orders.
- Market contracts are immutable dataclasses.
- Supabase persistence is behind a repository protocol and optional.
- Tracker remains preserved and separate.
- Hard risk configuration is outside strategy output.

Phase 2 should keep the same dependency direction:

`market -> strategy -> decision -> risk -> execution`

No strategy module should import broker/execution code.

## Market data audit

- Public Binance Spot endpoints only.
- Timeout exists and retry/backoff is added by this audit.
- Closed candles only after this audit.
- A transient failure for one symbol no longer aborts all candidates.
- Timestamps remain Binance millisecond timestamps in the market contract.
- No live WebSocket dependency is required for Phase 1.

Still open:

- cache repeated higher-timeframe klines;
- weight-aware request budget;
- optional bounded concurrency;
- explicit clock synchronization/observability if Testnet execution is introduced later.

## Scanner audit

Current filters cover:

- quote asset;
- Spot/TRADING status;
- selected stablecoin bases;
- common leveraged suffixes;
- selected wrapped assets;
- minimum 24h quote volume;
- minimum trade count;
- minimum closed-candle history.

The ranking remains a research-priority score, not BUY/SELL. Liquidity contributes with a cap; directional agreement and volume expansion contribute to ranking. This is acceptable for Phase 1, but the score must not be reused as strategy confidence in Phase 2.

## Indicators / look-ahead

- EMA uses an SMA seed and deterministic recursive EMA.
- RSI and ATR use Wilder-style smoothing.
- Warmup checks are explicit.
- Flat RSI bug fixed.
- Closed-candle filtering is the key look-ahead protection added in this audit.
- Strategies/backtests must recompute indicators using only candles available at each historical timestamp.

## Market regime

Current ordering is:

1. high volatility;
2. bullish;
3. bearish;
4. ranging fallback.

This is deterministic and understandable. Thresholds are heuristic and should remain configuration/research parameters until historical validation. Do not auto-optimize them against the full backtest period.

## Security audit

Repository search found no use of:

- `/api/v3/order`;
- Futures `fapi`;
- Margin;
- withdrawals/`sapi`;
- private account endpoints.

No real Binance credentials are committed. `.env` is ignored. Service-role Supabase credentials remain backend-only by design.

RLS hardening is included in migration 003.

## Tests / CI

The existing GitHub Actions workflow on `main` completed successfully before audit changes, running:

- `ruff check app tests`
- `pytest -q`

This audit adds regression coverage for:

- filtering an open/incomplete candle;
- transient network retry;
- flat RSI;
- USD1 stablecoin exclusion;
- partial per-symbol scanner failure.

The audit branch must pass the same CI before merge.

## Readiness for Phase 2

**READY AFTER THIS AUDIT PR PASSES CI AND IS MERGED.**

Phase 2 requirements:

- normalized Strategy interface/contract;
- Trend Following, Pullback, Breakout, Mean Reversion, Momentum;
- strategies consume closed-candle MarketCandidate/TimeframeAnalysis only;
- strategy outputs cannot execute orders;
- independent tests per strategy;
- no strategy score may bypass the future Risk Manager;
- explicit evidence/reasons on every result;
- historical tests must prevent look-ahead.

## Open debt before later execution phases

Before Paper Trading/Testnet:

- idempotent market-observation persistence;
- retention policy;
- order-book spread/depth;
- request-budget monitoring/caching;
- payload/schema versioning;
- portfolio synchronization contract with the existing tracker.
