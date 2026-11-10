# HANDOFF - Crypto System after Phase 5C

## Current state

Phases 1-4 are complete.

Phase 5 now contains:

- 5A future-outcome labels;
- 5B deterministic Spot backtest;
- 5C chronological calibration/validation/out-of-sample validation.

## Validation boundary

Default split:

- calibration 60%;
- validation 20%;
- out-of-sample 20%.

No shuffling.

Candles are truncated at each segment end so future segments cannot leak into earlier evaluation.

## Diagnostics

Per strategy:

- backtest metrics in each segment;
- expectancy-sign consistency;
- OOS/calibration expectancy ratio;
- drawdown degradation;
- performance by market regime;
- score-threshold sensitivity;
- WATCH vs REJECT future outcomes.

## No autonomous tuning

The validation layer does not change:

- strategy thresholds;
- strategy weights;
- hard risk limits;
- kill switch.

It only reports evidence.

## Important next step

Do not go directly to Testnet.

The framework is ready, but we still need **Phase 5D: a real evidence run over sufficiently deep public Binance history across multiple liquid Spot assets**.

That run should establish actual sample sizes, regime coverage and out-of-sample stability before any signed exchange API is introduced.
