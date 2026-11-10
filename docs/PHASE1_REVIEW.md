# Phase 0 Review and Phase 1 Corrections

## Findings

### 1. Market source and execution environment were coupled

Phase 0 exposed `BINANCE_TESTNET` but did not distinguish where public market analysis should come from. Phase 1 introduces `BINANCE_MARKET_BASE_URL=https://api.binance.com` separately. This keeps market intelligence representative while execution remains disabled/Testnet-only.

### 2. Scanner was only a symbol-name filter

The original scanner excluded some stable/leveraged symbols but had no exchange metadata, liquidity, candles, indicators, market regime or minimum-history validation. It has been replaced with a multi-stage scanner.

### 3. Mutable Pydantic list defaults

`StrategySignal.reasons` and `RiskDecision.reasons` used `[]` as defaults. Pydantic v2 generally isolates model defaults, but explicit factories are clearer and safer. Phase 1 updates these models.

### 4. Dependency set was larger than Phase 1 required

Pandas, NumPy, SQLAlchemy and Psycopg were declared but unused. Phase 1 market logic is pure Python, keeping dependencies smaller. Database integration is isolated behind a repository adapter.

### 5. Virtual environment was present inside the working tree

`.venv` and bytecode artifacts were removed. `.gitignore` already excludes them.

### 6. Supabase persistence needed to be optional

Tests should not need cloud credentials. A null repository is the default and Supabase is opt-in.

### 7. Ranking vs trading signal needed a hard semantic boundary

Market candidates now have a `ranking_score`, explicitly not a BUY/SELL score. Strategies do not exist in Phase 1.

## Remaining technical debt

- REST calls are synchronous; acceptable for the first scanner, but a later performance pass may use bounded async concurrency.
- No local cache yet; frequent scans would re-download all four timeframe series.
- Wrapped-token exclusion is conservative/static and should eventually be metadata-driven.
- Stablecoin list is static and must be maintained.
- No order-book spread filter yet; Phase 1 uses 24h quote volume and trade count as liquidity proxies.
- Market-regime thresholds are heuristics and must be evaluated out-of-sample before influencing trades.
