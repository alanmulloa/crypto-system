# Phase 5J — Phase 6 Readiness & Governance

Phase 5J prepares a formal, auditable path toward future Binance Spot Testnet
without enabling Testnet, private APIs or order placement.

## 5J.1 Research gate snapshot

A prospective experiment can enter readiness review only when both are true:

- `decision = PASS_RESEARCH`
- `sample_ready = true`

Even then, `phase6_blocked = true`.

## 5J.2 Risk preflight

The runtime safety baseline is inspected without exposing credentials.

Readiness expects:

- `TRADING_MODE=PAPER`
- `BINANCE_TESTNET=true`
- `KILL_SWITCH=true`
- positive position, daily-buy and daily-loss limits
- configured cash-reserve and open-position limits

Presence of API key/secret is recorded only as booleans.

## 5J.3 Execution boundary

The readiness boundary hard-codes:

```text
spot_only = true
futures_allowed = false
margin_allowed = false
leverage_allowed = false
withdrawals_allowed = false
live_orders_allowed = false
testnet_orders_allowed = false
private_api_use_allowed = false
automatic_activation_allowed = false
```

## 5J.4 Human approval artifact

Human approval can authorize only:

```text
TESTNET_PREPARATION_ONLY
```

It cannot authorize Testnet orders or live orders.

## 5J.5 Readiness decision

Possible states include:

- `BLOCKED_RESEARCH`
- `BLOCKED_RISK_PREFLIGHT`
- `BLOCKED_EXECUTION_BOUNDARY`
- `READY_FOR_HUMAN_APPROVAL`
- `APPROVED_FOR_TESTNET_PREPARATION`

None of these makes `phase6_eligible=true`.

## 5J.6 Testnet dry-run plan

A readiness-approved experiment can generate an informational Testnet
preparation plan. The plan:

- makes no private API calls
- submits no orders
- writes no credentials
- changes no runtime mode
- keeps Phase 6 blocked

## 5J.7 Governance invariant

Phase 6 activation remains a separate future implementation and human decision.
No Phase 5J result can automatically enable Testnet execution.
