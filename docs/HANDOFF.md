# HANDOFF - Crypto System after Phase 3C

## Current state

Phases 1 and 2 are complete. Phase 3 now includes:

- portfolio contract;
- hard portfolio-aware risk;
- one-way tracker synchronization;
- custody/liquidity exposure diagnostics;
- real daily-buy usage from the tracker operation journal.

The tracker remains authoritative for portfolio state.

## Important safety change

The bridge no longer claims daily realized PnL is zero.

The current operation journal cannot calculate realized PnL rigorously, so:

`daily_realized_pnl_usd = null`

The Risk Manager blocks new BUY approvals while this value is unavailable.

This prevents an unknown daily-loss state from silently bypassing the loss limit.

## Exposure diagnostics

`analyze_exposure()` reports:

- exact single-source custody exposure;
- multi-source unattributed value;
- unknown custody value;
- known liquid value;
- explicit/inferred illiquid value;
- unknown liquidity value.

Multi-source positions are not divided equally.

## Tracker bridge

`dailyBuyUsedUsdV48_()` now calculates today's executed purchases from `Operaciones ejecutadas`.

## Next task

Phase 4 should introduce the Paper Broker and, as part of its fill/trade journal, create an auditable realized-PnL ledger. Only then should the daily loss guard be considered complete for automated paper execution.

Still prohibited:

- real trading;
- Binance private trading API;
- Futures/Margin/leverage;
- withdrawals;
- agent write-back to tracker.
