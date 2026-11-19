# Phase 8A–8H — Web + Agent Integration

This large product-integration deliverable connects the existing Crypto Tracker
web app to the Trading Agent without turning research signals into executable
investment instructions.

## 8A — Agent Dashboard Contract

The Agent exposes a stable read-only dashboard projection from the latest
synchronized portfolio.

## 8B — Latest Portfolio Read Model

Supabase and in-memory repositories can return the latest Tracker export for the
dashboard projection.

## 8C — Portfolio + Exposure View

The dashboard returns total portfolio, cash/reserve/deployable cash, capital at
risk, daily buy capacity, allocation targets, custody exposure and liquidity
quality. Multi-custody positions are not fake-split between providers.

## 8D — Safety / Execution State

The web can see trading mode, kill switch, testnet flag and the hard execution
boundary. Real trading, automatic orders, withdrawals, Futures, Margin and
leverage remain disabled.

## 8E — Recommendation Source Separation

Every asset carries an explicit Agent recommendation object. Until prospective
research passes its separate gate it is:

```text
state = RESEARCH_ONLY
action = NO_VALIDATED_AGENT_SIGNAL
authoritative = false
```

Legacy Tracker recommendations remain visible but are not represented as
validated Agent recommendations.

## 8F — Apps Script Agent Bridge

The Tracker reads `GET /portfolio/dashboard` with the existing bearer token.
Responses are cached briefly and failures degrade gracefully.

Required Script Properties:

```text
CRYPTO_AGENT_BASE_URL
CRYPTO_AGENT_SYNC_TOKEN
```

## 8G — Unified Web Panel

The existing web gains an Agent panel with operational state, synchronized
portfolio value, deployable cash, capital at risk, remaining daily buy capacity,
recommendation status and daily-loss-guard availability.

## 8H — Integration Guardrails

This phase does not place orders, change research definitions, promote Phase 6,
expose private exchange credentials, or auto-execute Tracker recommendations.

```text
phase6_eligible = false
phase6_blocked = true
automatic_execution = false
human_confirmation_required = true
```
