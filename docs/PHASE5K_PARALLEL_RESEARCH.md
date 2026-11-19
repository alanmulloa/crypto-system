# Phase 5K — Parallel Research Pipeline

Phase 5K opens a second research lane while XRP Phase 5G continues collecting
genuinely unseen prospective evidence.

## 5K.1 Fixed research universe

The first campaign is pre-registered before observing any campaign outcomes:

```text
campaign: core-mean-reversion-forward-2026-11
symbols: BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT
strategy: mean_reversion
ruleset: existing Phase 5F.1 predefined buckets only
outcome: 24h
fee: 10 bps
slippage: 5 bps
```

No new thresholds are optimized from campaign data.

## 5K.2 Fixed prospective research window

```text
start: 2026-11-20T00:00:00Z
end:   2027-05-19T00:00:00Z
```

Before the end timestamp the campaign is only `PLANNED` or `COLLECTING`.
Candidate screening is prohibited until the fixed window has completed.

## 5K.3 Evidence + screening

After maturity, the campaign reuses the existing public-Binance evidence stack
and `MeanReversionEntryDiagnostics`.

Candidate selection still uses calibration + validation only. The generated OOS
segment is descriptive and cannot enter candidate selection.

## 5K.4 Existing proposal gate

Every discovered proposal passes through the existing Phase 5H.5 gate:

- exact definitions -> `ALREADY_TRACKED`
- overlapping families -> `HUMAN_REVIEW`
- weak validation -> `REJECT_WEAK_VALIDATION`
- otherwise -> eligible for research-portfolio review

## 5K.5 Research portfolio budget

At most two new concurrent research experiments may be queued by this campaign.
The queue also limits one newly queued proposal per symbol and per feature.

These controls prevent research sprawl; they do not change trading risk limits.

## 5K.6 Human registration queue

A successful proposal becomes:

```text
READY_FOR_HUMAN_REGISTRATION
```

It is never written to the experiment registry automatically. A human must still
register it as `DRAFT` and move it through 5H calibration/validation.

## 5K.7 Scheduled campaign monitor

The weekly GitHub workflow checks campaign maturity. Before maturity it produces
status only. After maturity it may build screening/queue artifacts, still with no
registry writes.

## 5K.8 Research portfolio dashboard artifact

The dashboard summarizes campaign state and proposals awaiting human
registration. It never authorizes Phase 6.

XRP Phase 5G is not changed or replaced by Phase 5K.
