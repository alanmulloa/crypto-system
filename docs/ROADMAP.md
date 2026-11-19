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

#### Phase 5H.8 - Freeze Review Protocol ✅
- requires PASS_CALIBRATION + PASS_VALIDATION artifacts
- full experiment-definition snapshots required
- exact registry/artifact definition equality
- READY_FOR_FREEZE / NOT_READY_FOR_FREEZE / INCONCLUSIVE
- no registry writes or automatic freeze
- Phase 6 remains blocked

#### Phase 5H.9 - Freeze Manifest ✅
- deterministic pre-freeze definition fingerprint
- canonical SHA-256 fingerprints for calibration/validation evidence
- rechecks 5H.8 readiness before manifest creation
- freeze timestamp remains pending
- no registry writes or automatic freeze
- Phase 6 remains blocked

#### Phase 5H.10 - Generic Prospective Bootstrap ✅
- generic protocol derived only from FROZEN registry experiments
- freeze manifest fingerprint verification
- registry-defined outcome horizon, fees and slippage
- strictly post-freeze observations
- immutable history/continuity gate
- adapter layer only; existing XRP 5G remains untouched
- no Testnet, execution or automatic promotion

#### Phase 5H.11 - Generic Prospective Review / Decision ✅
- WAITING_FOR_CANDIDATE_SIGNAL / WAITING_FOR_MATURITY
- ACCUMULATING_MATURED_SAMPLE / REVIEW_REQUIRED
- NOT_READY / INCONCLUSIVE / PASS_RESEARCH / FAIL_RESEARCH
- pre-registered return, positive-rate and uplift criteria
- integrity and frozen-definition validation required
- PASS_RESEARCH never unblocks Phase 6
- existing XRP 5G remains untouched

#### Phase 5H.12 - Generic Signal Evaluator ✅
- resolves frozen feature/operator/threshold against signal-time data
- supports all discovery features eligible for generic prospective research
- requires matching symbol, strategy, WATCH state and direction

#### Phase 5H.13 - Public Generic Prospective Runner ✅
- reuses BinancePublicClient + HistoricalSanityRunner
- public Spot data only; no credentials
- pre-freeze data is lookback only
- emits the 5H.10 prospective contract

#### Phase 5H.14 - Multi-experiment Planner ✅
- separates canonical XRP 5G from generic Phase 5H experiments
- FROZEN -> bootstrap required
- generic PROSPECTIVE -> collect evidence
- no automatic lifecycle transitions

#### Phase 5H.15 - Scheduled Generic Orchestrator ✅
- runs every six hours
- public data -> continuity -> immutable history -> review -> decision
- no-op when no generic PROSPECTIVE experiment exists
- canonical XRP remains on Phase 5G

#### Phase 5H.16 - Research Lineage Audit ✅
- verifies artifact phases, experiment ids and frozen fingerprints
- detects definition drift
- verifies Phase 6 remains blocked

#### Phase 5H.17 - Human Review Dossier ✅
- consolidated experiment status, progress, decision and next allowed action
- phase6_eligible=false for every research experiment
- no automatic promotion

#### Phase 5H.18 - Research Infrastructure Completion ✅
- README / roadmap / architecture reconciled
- generic future-candidate path complete
- XRP 5G compatibility preserved
- Phase 6 remains a separate human gate

### Phase 5I - Research Operations & Observability ✅
- 5I.1 evidence freshness monitor
- 5I.2 prospective signal-scarcity monitor
- 5I.3 consolidated research-health states
- 5I.4 operational action queue with no registry writes
- 5I.5 scheduled read-only health report every 12 hours
- 5I.6 no-signal periods cannot alter frozen research definitions
- Phase 6 remains blocked

### Phase 5J - Phase 6 Readiness & Governance ✅
- 5J.1 research gate snapshot from prospective PASS_RESEARCH + sample_ready
- 5J.2 runtime risk preflight with credential-presence booleans only
- 5J.3 restrictive Spot-only execution boundary
- 5J.4 explicit human approval artifact for TESTNET_PREPARATION_ONLY
- 5J.5 auditable readiness states; no automatic activation
- 5J.6 informational Testnet dry-run plan with zero API calls/orders
- 5J.7 Phase 6 remains blocked until a separate future activation decision

### Phase 5K - Parallel Research Pipeline 🔬
- 5K.1 fixed five-symbol Mean Reversion research universe
- 5K.2 pre-registered future campaign window: 2026-11-20 -> 2027-05-19 UTC
- 5K.3 existing 5F.1 diagnostics reused after campaign maturity
- 5K.4 existing proposal gate reused; no threshold optimization
- 5K.5 maximum two concurrent new research experiments with diversity limits
- 5K.6 READY_FOR_HUMAN_REGISTRATION queue; no automatic registry writes
- 5K.7 weekly campaign maturity/screening workflow
- 5K.8 research portfolio dashboard artifact
- XRP Phase 5G continues independently and unchanged

### Phase 5L - Research Campaign Operations ✅
- 5L.1 deterministic campaign progress / elapsed / remaining / percent
- 5L.2 public Spot market-data health across 15m/1h/4h/1d
- 5L.3 screening readiness requires fixed-window completion + data health + fingerprint integrity
- 5L.4 Phase 5K promotion queue surfaced without registry writes
- 5L.5 consolidated campaign operations dashboard artifact
- 5L.6 daily read-only workflow
- 5L.7 no automatic screening/registration and Phase 6 remains blocked

### Phase 5M - Campaign Evidence Durability & Alerts ✅
- 5M.1 immutable daily Phase 5L operations history
- 5M.2 continuity + campaign fingerprint drift gate
- 5M.3 operational incident detector for gaps/staleness/duplicates/Spot availability
- 5M.4 durable repository history beyond temporary workflow artifacts
- 5M.5 daily scheduled persistence and incident refresh
- 5M.6 no strategy mutation, registration or Phase 6 activation

### Phase 5N - Incident Response & Recovery ✅
- deterministic incident-to-action recovery plan
- all recovery actions require human review
- no strategy changes or registry writes

### Phase 5O - Research Reproducibility ✅
- deterministic SHA-256 manifest over campaign + operations + incidents + recovery
- exact-input verification
- no automatic repair

### Phase 5P - Human Campaign Review Pack ✅
- progress + readiness + incidents + recovery + reproducibility
- explicit human-review states
- no automatic screening

### Phase 5Q - Research Operations Hardening ✅
- consolidated governance status
- operational-health + reproducibility checks
- Phase 6 eligibility remains false
- campaign operations hardening complete when healthy and reproducible

### Phase 5R - Shared Research Main-Writer Lock ✅
- Phase 5G / generic 5H / Phase 5M writers share one concurrency group
- cancel-in-progress remains false

### Phase 5S - Safe Evidence Push Protocol ✅
- all research main-writers fetch full history
- git pull --rebase origin main before push
- conflicts fail safely; no forced push

### Phase 5T - Writer Policy Audit ✅
- deterministic CI audit of writer permissions, lock, checkout and push policy
- workflow changes cannot silently bypass writer hardening

### Phase 5U - Research Writer Hardening Completion ✅
- automated research evidence writes are serialized and auditable
- no strategy/lifecycle/Phase 6 behavior changed

### Phase 5V - Unified Research State ✅
- one control-plane artifact across registry, XRP 5G, campaign governance and writer policy

### Phase 5W - Research Blocker Graph ✅
- explicit blockers with no automatic remediation

### Phase 5X - Human Action Inbox ✅
- only explicit human research/review/screening actions surfaced

### Phase 5Y - Material State Change Detection ✅
- ignores timestamp-only churn and reports material control-plane changes

### Phase 5Z - Research Control Plane Completion ✅
- single read-only operational snapshot with SHA-256
- Phase 6 remains ineligible and blocked

### Phase 5AA - Durable Control-Plane State ✅
- last material control-plane state persists across scheduled runs

### Phase 5AB - Material Transition Ledger ✅
- immutable history/events only when state changes materially
- timestamp-only churn creates no repository commit

### Phase 5AC - Stable Human Action / Blocker IDs ✅
- deterministic IDs prevent duplicate action noise across runs

### Phase 5AD - Control Plane Main-Writer Integration ✅
- fourth writer joins shared research-main-writer lock and safe rebase protocol
- writer policy audit covers control-plane persistence

### Phase 5AE - Control-Plane Durability Completion ✅
- first/no-change/state-transition semantics are durable across runs
- Phase 6 remains blocked

### Phase 5AF - In-run Campaign Governance Rebuild ✅
- control plane rebuilds 5N-5Q from durable 5M inputs before evaluation

### Phase 5AG - In-run Writer Policy Rebuild ✅
- writer policy is regenerated from current workflow files every control-plane cycle

### Phase 5AH - Explicit Dependency Status ✅
- XRP evidence, campaign inputs/governance and writer policy readiness are explicit

### Phase 5AI - Bootstrap-Aware Control Plane ✅
- WAITING_FOR_DEPENDENCIES distinguishes normal bootstrap from research failure

### Phase 5AJ - Scheduled Governance Consolidation ✅
- control plane owns scheduled governance synthesis
- standalone 5N-5Q workflow remains manual diagnostic tooling

## Phase 6 - Binance Spot Testnet ⛔ BLOCKED
- requires genuinely unseen prospective evidence and a separate human decision
- sample_ready and PASS_RESEARCH do not automatically unblock Phase 6
- no signed/private API execution is enabled by Phase 5G or Phase 5H

## Phase 7 - External Signals
## Phase 8 - Dashboard Integration
## Phase 9 - Auto Limited
