# Phase 2B - Strategy Aggregator

## Purpose

Phase 2B compares the independent Phase 2A strategy assessments and produces one research-level state for a symbol.

Output remains limited to:

- WATCH
- WAIT
- REJECT

A BUY/SELL direction is still a hypothesis only. No order, sizing or broker call is created.

## Conflict model

The aggregator intentionally does not average all strategy scores blindly.

Each directional assessment contributes support using:

`score x confidence x state_weight`

where:

- WATCH weight = 1.0
- WAIT weight = 0.35
- REJECT weight = 0

BUY and SELL support are accumulated separately.

If the losing direction has at least 65% of the winning-direction support, the result is:

- WAIT
- no preferred direction

This makes disagreement explicit instead of hiding it inside an average.

## WATCH rule

The aggregate reaches WATCH only when:

- at least two WATCH assessments support the same direction;
- weighted strategy score is at least 70;
- weighted confidence is at least 60;
- opposite-direction conflict remains below the conflict threshold.

Otherwise the result remains WAIT.

## Safety boundary

The aggregator:

- does not import Risk Manager;
- does not know portfolio balances;
- does not size positions;
- does not access Binance private APIs;
- does not create orders.

Dependency direction remains:

`market -> independent strategies -> aggregator -> future historical validation -> portfolio/risk -> execution`

## Next step - Phase 2C

Build historical sanity tooling that evaluates strategy behavior using only candles available at each historical timestamp.

The purpose of 2C is not yet optimization. It is to verify:

- no look-ahead;
- deterministic strategy outputs;
- reasonable signal frequency;
- contradictory-strategy behavior;
- state transitions through time.
