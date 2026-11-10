# HANDOFF - Crypto System after Phase 1

## Current state

Phase 0 foundation is preserved and Phase 1 Market Intelligence is implemented. The tracker remains under `tracker/apps-script/crypto_tracker_v4_7_1_full/` and has not been functionally replaced.

The agent can now use Binance public Spot endpoints without API keys to:

- read exchange metadata;
- read 24h tickers;
- download 15m, 1h, 4h and 1d candles;
- filter liquid USDT Spot markets;
- exclude stablecoin bases, leveraged-token suffixes and selected wrapped duplicates;
- reject insufficient history;
- compute EMA, RSI, ATR, volume ratio and simple market structure;
- classify market regime;
- rank research candidates.

It cannot generate BUY/SELL strategy signals or place orders.

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
- public market source is independent from future execution/Testnet configuration.

## Important files

- `agent/app/market/binance_public.py`
- `agent/app/market/indicators.py`
- `agent/app/market/regime.py`
- `agent/app/market/scanner.py`
- `agent/app/market/service.py`
- `agent/app/market/cli.py`
- `agent/app/storage/market_repository.py`
- `supabase/migrations/002_market_intelligence.sql`
- `docs/PHASE1_REVIEW.md`

## Validation performed in source environment

Because package installation/network access is restricted in the source build environment, the full dependency-based `pytest`/`ruff` CI could not run there. Pure Market Intelligence tests were executed with stdlib `unittest` and passed 7/7. Python compile checks were also run before packaging.

GitHub Actions is configured to install dependencies and run both `ruff check app tests` and `pytest -q` on push/PR.

## Next agent task - Phase 2

Review Phase 1 first. Then implement a normalized strategy interface for trend following, pullback, breakout, mean reversion and momentum. Strategies may consume MarketCandidate/TimeframeAnalysis but must not access brokers or private APIs. Strategy outputs need score, confidence, direction hypothesis, entry/invalidation context and explicit reasons. Add conflict aggregation only after each strategy has unit tests. Do not implement order execution.

Before merging Phase 2, run historical sanity checks to ensure indicators and candles use only information available at each timestamp.
