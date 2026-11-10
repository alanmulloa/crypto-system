# HANDOFF - Crypto System after Phase 2B

## Current state

Phase 1 Market Intelligence is hardened. Phase 2A implements five independent strategy hypotheses. Phase 2B adds a conflict-aware Strategy Aggregator.

The system can now:

1. scan Binance public Spot market data;
2. analyze closed candles only;
3. classify market regime;
4. evaluate Trend, Pullback, Breakout, Mean Reversion and Momentum independently;
5. compare BUY/SELL hypothesis support;
6. output a research state of WATCH / WAIT / REJECT.

It still cannot size or execute an order.

## Aggregation invariants

- no blind averaging of opposing strategies;
- BUY and SELL support are calculated separately;
- strong opposite-direction support forces WAIT with no preferred direction;
- WATCH requires at least two independent WATCH assessments agreeing;
- rejected strategies contribute no directional strength;
- Phase 1 ranking_score is not used by the aggregator;
- no portfolio or Risk Manager inputs are used.

## Important files

- `agent/app/strategies/aggregator.py`
- `agent/tests/test_strategy_aggregator.py`
- `docs/PHASE2B_STRATEGY_AGGREGATOR.md`

## Security invariants

Unchanged:

- Spot only;
- no private Binance trading APIs;
- no Futures/Margin/leverage;
- no withdrawals;
- no real trading;
- no strategy or aggregator may import execution;
- hard risk limits stay outside strategy control.

## Next task - Phase 2C

Implement a historical sanity runner before Phase 3.

It must feed strategies only information available at each historical timestamp and verify deterministic behavior/state transitions. It should not optimize thresholds yet and must not perform order execution.

After 2C, Phase 3 can integrate the existing tracker portfolio and hard Risk Manager.
