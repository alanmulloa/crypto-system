# Roadmap

## Phase 0 - Foundation ✅
## Phase 1 - Market Intelligence ✅
## Phase 2 - Strategies ✅
## Phase 3 - Portfolio + Risk ✅
## Phase 4 - Paper Trading ✅

## Phase 5 - Backtesting + Evaluation

### Phase 5A - Outcome Evaluation ✅
### Phase 5B - Deterministic Spot Backtest ✅
### Phase 5C - Temporal Validation ✅

### Phase 5D - Real historical evidence tooling ✅
- paginated public Binance klines
- 15m / 1h / 4h / 1d
- closed-candle filtering
- deduplication
- gap diagnostics
- historical/live 250-candle parity
- multi-asset evidence runner
- JSON evidence artifact
- no credentials or execution

### Phase 5E - Evidence review ✅
- real 730-day evidence reviewed
- all five current strategy backtests negative in aggregate OOS
- mean_reversion WATCH outcomes identified as the primary research lead
- no approval for Testnet

### Phase 5F - Strategy diagnostics & exit research ✅
- path-level MFE / MAE and timing
- current-exit diagnostics
- fixed-horizon comparison
- predetermined ATR stop/target sensitivity
- symbol / regime / temporal-segment breakdowns
- observed OOS treated as descriptive only
- no strategy rule changes
- no Testnet or execution
- review conclusion: no stable exit-only variant justified
- Phase 5G deferred pending entry-quality evidence

### Phase 5F.1 - Mean Reversion entry-quality diagnostics ✅
- signal-time features only
- fixed score / confidence bands
- 1h RSI, ATR%, volume and EMA-distance context
- 15m and 4h alignment context
- 1h EMA20/EMA50 spread
- symbol and market-structure breakdowns
- repeated WATCH BUY clustering / cooldown evidence
- per-symbol and pooled five-symbol reports
- calibration + validation only for candidate screening
- previously observed OOS remains descriptive only
- real 730-day run reviewed
- no pooled bucket has positive return in both calibration and validation
- XRPUSDT volume_ratio_1h <= 0.75 is the strongest asset-specific research lead
- ETHUSDT 4h lower-highs/lower-lows is a weaker secondary lead

### Phase 5F.2 - Mean Reversion candidate experiment ✅
- predetermined XRPUSDT low-1h-volume candidate
- ETHUSDT 4h lower-highs/lower-lows comparator
- baseline vs candidate metrics by temporal segment
- calibration + validation determine eligibility
- XRP candidate passed the predefined research screen
- ETH comparator passed mechanically but with weak validation uplift
- observed OOS remains descriptive only
- no production strategy changes
- no Testnet or execution

### Phase 5G - Frozen XRP prospective evidence 🔬
- frozen candidate: XRPUSDT Mean Reversion WATCH BUY with volume_ratio_1h <= 0.75
- freeze cutoff: 2026-11-10T22:10:15.195720+00:00
- only post-freeze signals count as prospective observations
- pre-freeze history may be used only for indicator lookback
- baseline XRP cohort vs candidate subset
- 24h fixed outcome with existing fee/slippage assumptions
- no Testnet or execution

#### Phase 5G.1 - Automated evidence collection ✅
- scheduled public-Binance collection
- immutable history and continuity/integrity gate

#### Phase 5G.2 - Monitoring & review ✅
- WAIT / REVIEW monitoring state
- progress and milestone reporting

#### Phase 5G.3 - Prospective decision protocol ✅
- pre-registered NOT_READY / INCONCLUSIVE / PASS_RESEARCH / FAIL_RESEARCH
- PASS_RESEARCH is not execution approval

#### Phase 5G.4 - Accumulate prospective evidence 🔬
- currently collecting genuinely unseen evidence
- sample_ready does not authorize progression
- no automatic promotion rule

### Phase 5H - Research experiment infrastructure

#### Phase 5H.0 - Current status / roadmap reconciliation ✅
- README and roadmap reconciled with the implemented system

#### Phase 5H.1 - Research Experiment Registry ✅
- deterministic JSON registry
- explicit experiment lifecycle
- immutable definition from FROZEN onward
- existing XRP 5G represented as metadata only

#### Phase 5H.2 - Candidate Research Workspace ✅
- isolated local workspace for DRAFT / CALIBRATION / VALIDATION experiments
- deterministic definition snapshot and registry-drift validation
- XRP 5G PROSPECTIVE experiment explicitly excluded
- research_only=true and phase6_blocked=true guardrails
- no network, execution, Testnet, or candidate discovery

#### Phase 5H.3 - Candidate Registration + Transition Flow ✅
- explicit DRAFT-only registration
- duplicate-id and definition validation
- lifecycle transitions through the existing state graph
- explicit freeze timestamp required for FROZEN
- existing XRP 5G cannot be rewound or mutated

#### Phase 5H.4 - Candidate Discovery ✅
- consumes existing Phase 5F.1 artifacts
- uses calibration + validation only
- only pre-defined buckets with exact rule mappings are eligible
- requires sufficient sample + positive return + positive uplift in both segments
- deterministic research proposals; no automatic registry writes or freezing
- OOS remains descriptive and is excluded from selection

#### Phase 5H.5 - Proposal Review Gate ✅
- exact tracked rules -> ALREADY_TRACKED
- overlapping research families -> HUMAN_REVIEW
- validation uplift < 0.10 pp -> REJECT_WEAK_VALIDATION
- otherwise -> READY_TO_REGISTER
- read-only registry review; no automatic registration or freezing
- Phase 6 remains blocked

#### Phase 5H.6 - Calibration Harness ✅
- requires an explicitly registered CALIBRATION experiment
- consumes calibration bucket summaries only
- minimum 20 observations
- positive average + median return
- positive rate > 50% and uplift > 0
- validation and OOS are not read
- no automatic lifecycle transition

#### Phase 5H.7 - Validation Harness ✅
- requires an explicitly registered VALIDATION experiment
- consumes validation bucket summaries only
- minimum 20 observations
- positive average + median return
- positive rate > 50%
- validation uplift >= 0.10 pp
- calibration and OOS are not read
- PASS_VALIDATION only enables a separate human freeze review

## Phase 6 - Binance Spot Testnet ⛔ BLOCKED
- requires genuinely unseen prospective evidence and a separate human decision
- sample_ready and PASS_RESEARCH do not automatically unblock Phase 6
- no signed/private API execution is enabled by Phase 5G or Phase 5H

## Phase 7 - External Signals
## Phase 8 - Dashboard Integration
## Phase 9 - Auto Limited
