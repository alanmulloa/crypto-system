# Phase 8Q–8X — Portfolio History & Control Center

This macro-deliverable turns the integrated web into an operational portfolio
control center instead of a current-state-only dashboard.

## 8Q — Portfolio Snapshot History

The Agent can read recent append-only portfolio snapshots from the existing
`portfolio_syncs` store.

## 8R — Value-Change Windows

The Agent derives 24h / 7d / 30d portfolio value changes from available
snapshots.

These metrics are deliberately named **value change**, not investment return.
They are not adjusted for deposits, withdrawals, buys, sells or other flows.

## 8S — Historical API

`GET /portfolio/history?limit=90` exposes:

- snapshot count
- latest timestamp
- total/cash/capital-at-risk series
- 24h / 7d / 30d value changes
- explicit metric semantics

The endpoint uses the same bearer-token boundary as the existing portfolio
dashboard.

## 8T — Bounded History Read

Supabase history reads are capped at 365 snapshots per request. The dashboard
uses 90 by default.

## 8U — Apps Script History Bridge

The Agent bridge fetches dashboard + history together and degrades gracefully
if historical data is not yet available.

## 8V — Portfolio Evolution Panel

The web shows:

- 24h / 7d / 30d value change
- recent portfolio sparkline
- snapshot count
- latest synchronized snapshot timestamp
- a clear warning that value change is not flow-adjusted return

## 8W — One-click Agent Sync

The web adds **Sincronizar Agent**:

1. exports the current Tracker portfolio
2. sends the snapshot to Agent
3. invalidates the short Agent cache
4. reloads the unified dashboard

It does not create orders or alter research state.

## 8X — Control Center Guardrails

- historical metrics do not claim trading performance
- no automatic execution
- no withdrawals
- no private exchange credential exposure
- Phase 6 remains blocked
