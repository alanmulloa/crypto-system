# HANDOFF - Crypto System after Phase 2C

## Current state

Phase 1 Market Intelligence is hardened. Phase 2A has five independent strategy hypotheses. Phase 2B aggregates them with explicit conflict handling. Phase 2C adds a deterministic walk-forward historical sanity runner.

The system still cannot execute trades or simulate a portfolio.

## Historical safety invariant

At historical timestamp T, the strategy layer only receives candles with:

`close_time_ms <= T`

A regression test mutates future candles and proves that the candidate, all strategy assessments and aggregate output at the prior timestamp remain identical.

Do not weaken this invariant.

## New files

- `agent/app/evaluation/historical.py`
- `agent/app/evaluation/metrics.py`
- `agent/tests/test_historical_sanity.py`
- `docs/PHASE2C_HISTORICAL_SANITY.md`

## Diagnostics

The historical runner can report:

- aggregate WATCH / WAIT / REJECT frequency;
- unresolved BUY/SELL conflicts;
- per-strategy WATCH / WAIT / REJECT frequency.

It is not yet a profitability backtester.

## Security invariants

Unchanged:

- Spot only;
- no real trading;
- no Binance private trading API;
- no Futures/Margin/leverage;
- no withdrawals;
- strategy/evaluation code cannot create orders;
- Risk Manager remains outside strategies;
- hard risk limits remain operator-controlled.

## Next task - Phase 3

Integrate the existing tracker portfolio into the agent through an explicit portfolio contract.

Phase 3 should:

1. represent holdings and custody;
2. preserve capital states such as SOLO GANANCIAS / capital pending / pool-staking;
3. calculate total exposure and available cash;
4. add portfolio-aware position sizing;
5. enforce hard risk limits;
6. combine aggregate research output with a separate RiskDecision;
7. still avoid real execution.

Before later Paper Trading, also resolve Phase 1 debt around observation idempotency/retention and execution-quality liquidity filters.
