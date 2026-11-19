# Phase 8I–8P — Wallet & Portfolio Productization

This macro-deliverable moves wallet/on-chain data from Tracker-only presentation
into the Agent's read model and unified web experience.

## 8I — Sync Contract 1.1

The Tracker portfolio sync remains backward-compatible and adds optional:

- wallet_rows
- onchain_rows
- onchain_reconciliation_rows

Existing 1.0 payloads remain valid.

## 8J — Wallet Inventory

The Agent projects wallets by name/network with:

- active state
- masked public address
- last sync
- freshness
- holdings count
- on-chain holdings

Full public addresses are not returned by the dashboard.

## 8K — Reconciliation Health

On-chain reconciliation is summarized as:

- healthy / needs review
- issue count
- asset
- wallet/network
- delta
- status
- notes

No automatic reconciliation or balance mutation is performed.

## 8L — Wallet Freshness

ISO timestamps are classified as FRESH/STALE using a fixed 24h operational
window. Unknown/non-ISO timestamps remain UNKNOWN rather than guessed.

## 8M — Agent Dashboard Enrichment

The existing Agent dashboard now includes wallet inventory and exposes wallet
health in data_quality.

## 8N — Tracker → Agent Wallet Sync

Apps Script exports the existing Wallets, On-chain balances and Conciliacion
on-chain sheets in the same portfolio snapshot.

## 8O — Unified Wallet Web Panel

The current web prioritizes Agent wallet/reconciliation data when available and
falls back to the existing Tracker rendering when Agent is offline.

## 8P — Product Guardrails

- read-only Agent dashboard
- no wallet private keys
- public addresses masked in UI payload
- no automated reconciliation writes
- no orders
- no withdrawals
- Phase 6 remains blocked
