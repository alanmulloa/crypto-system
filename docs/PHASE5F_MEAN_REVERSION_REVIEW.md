# Phase 5F - Mean Reversion evidence review

## Decision

Do **not** create a Phase 5G exit-tuning variant from this report.

The 5F diagnostics do not show an exit configuration that is positive and stable across
calibration and validation. The previously observed OOS data is descriptive only and
must not be used for parameter selection.

## Dataset

- 730 requested days
- BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT
- public Binance Spot market data only
- fee: 10 bps
- slippage: 5 bps
- maximum evaluation points: 8000
- OOS already observed before this review

Data quality is clean across the five symbols and all four intervals: no duplicate open
times and no reported gaps.

## Pooled exit evidence

Across all five symbols:

| Segment | Current exit | Fixed 4h | Fixed 8h | Fixed 12h | Fixed 24h | Fixed 48h |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Calibration | -0.426 | -0.324 | -0.385 | -0.534 | -0.829 | -1.320 |
| Validation | -0.238 | -0.177 | -0.078 | -0.021 | +0.267 | +1.206 |
| Observed OOS* | -0.449 | -0.223 | -0.228 | -0.278 | -0.178 | -0.434 |

Values are pooled net expectancy in USD per $100 research observation.

*Observed OOS is descriptive only. It is not eligible for selecting a new parameter.

The strong 24h/48h validation result is therefore not sufficient evidence for promotion:
it is absent in calibration and does not persist in the already-observed OOS period.

## ATR sensitivity

No tested stop/target ATR pair produces positive pooled expectancy in calibration.

Best pooled calibration row:

- stop 1.0 ATR
- target 0.75 ATR
- expectancy: -0.320 USD / observation

Best pooled validation row:

- stop 2.0 ATR
- target 2.0 ATR
- expectancy: -0.042 USD / observation

The two segments prefer materially different regions of the grid and neither produces a
positive, stable configuration. This is not a robust basis for an exit-rule variant.

## Path behavior

Across all five symbols:

- calibration: 1521 current-exit observations
- validation: 493 current-exit observations
- observed OOS: 558 current-exit observations
- favorable-then-loss: 752 / 251 / 271
- stop-before-later-recovery: 565 / 236 / 239

There is real evidence of premature stops in many paths, especially in validation.
However, widening stops or delaying exits is not enough: calibration remains negative
for every tested fixed horizon and ATR configuration.

This points to a more fundamental issue with entry quality / market-state selection,
not just exit mechanics.

## Phase 5G status

**Deferred.**

Phase 5G remains reserved for one narrow experimental strategy variant only after a
candidate rule is supported by calibration and validation evidence.

The next research task is entry-quality diagnostics for Mean Reversion. It should focus
only on information available at signal time and must not use future path data as an
entry feature.

Candidate dimensions to inspect:

- signal score / confidence bands
- normalized ATR / volatility context
- distance from reference mean / oversold depth
- short-term slope and momentum context
- multi-timeframe alignment
- symbol-specific behavior
- clustering / repeated signals from the same move
- cooldown or de-duplication of highly correlated consecutive signals

No private exchange API, Testnet or real execution is justified by this result.
