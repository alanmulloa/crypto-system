from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.config import Settings
from app.portfolio.exposure import analyze_exposure
from app.portfolio.sync import TrackerPortfolioExport
from app.portfolio.wallet_projection import build_wallet_inventory


def build_agent_dashboard(
    export: TrackerPortfolioExport,
    *,
    settings: Settings,
) -> dict[str, Any]:
    snapshot = export.to_snapshot(cash_asset=settings.portfolio_cash_asset)
    exposure = analyze_exposure(snapshot)
    total = snapshot.total_value_usd
    cash = snapshot.cash_value_usd
    reserve_required = total * (settings.min_cash_reserve_pct / 100.0)
    deployable = max(cash - reserve_required, 0.0)
    daily_buy_remaining = max(
        settings.max_daily_buy_usd - snapshot.daily_buy_used_usd,
        0.0,
    )
    wallet_inventory = build_wallet_inventory(
        wallet_rows=export.wallet_rows,
        onchain_rows=export.onchain_rows,
        reconciliation_rows=export.onchain_reconciliation_rows,
        as_of=export.generated_at,
    )

    assets = []
    for position in sorted(
        snapshot.positions,
        key=lambda item: item.market_value_usd,
        reverse=True,
    ):
        allocation = snapshot.allocation_for(position.asset)
        assets.append(
            {
                "asset": position.asset,
                "quantity": position.quantity,
                "market_value_usd": position.market_value_usd,
                "weight_pct": snapshot.weight_pct(position.asset),
                "avg_cost_usd": position.avg_cost_usd,
                "capital_pending_usd": position.capital_pending_usd,
                "capital_state": position.capital_state.value,
                "custody_sources": list(position.custody_sources),
                "liquidity_state": position.liquidity_state.value,
                "liquidity_basis": position.liquidity_basis,
                "target_weight_pct": (
                    allocation.target_weight_pct if allocation else None
                ),
                "max_weight_pct": (
                    allocation.max_weight_pct if allocation else None
                ),
                "agent_recommendation": {
                    "state": "RESEARCH_ONLY",
                    "action": "NO_VALIDATED_AGENT_SIGNAL",
                    "authoritative": False,
                    "max_notional_usd": 0.0,
                    "reason": (
                        "Agent investment signals are not exposed as actionable "
                        "until prospective research passes its separate gate."
                    ),
                },
            }
        )

    if settings.kill_switch:
        operational_state = "SAFETY_LOCKED"
    elif settings.trading_mode == "PAPER":
        operational_state = "PAPER_ONLY"
    else:
        operational_state = "REVIEW_REQUIRED"

    return {
        "schema_version": "8.0",
        "source": {
            "id": export.source_id,
            "revision": export.source_revision,
            "generated_at": export.generated_at.isoformat(),
            "content_hash": export.content_hash(),
        },
        "summary": {
            "total_value_usd": total,
            "cash_asset": settings.portfolio_cash_asset,
            "cash_value_usd": cash,
            "cash_weight_pct": (cash / total * 100.0) if total > 0 else 0.0,
            "capital_at_risk_usd": snapshot.capital_at_risk_usd,
            "open_positions": snapshot.open_positions,
            "daily_buy_used_usd": snapshot.daily_buy_used_usd,
            "daily_buy_remaining_usd": daily_buy_remaining,
            "minimum_cash_reserve_usd": reserve_required,
            "deployable_cash_usd": deployable,
        },
        "exposure": {
            **asdict(exposure),
            "custody": [asdict(item) for item in exposure.custody],
        },
        "safety": {
            "operational_state": operational_state,
            "trading_mode": settings.trading_mode,
            "kill_switch": settings.kill_switch,
            "binance_testnet": settings.binance_testnet,
            "real_trading_enabled": False,
            "testnet_orders_enabled": False,
            "automatic_orders_enabled": False,
            "withdrawals_enabled": False,
            "futures_enabled": False,
            "margin_enabled": False,
            "leverage_enabled": False,
            "phase6_eligible": False,
            "phase6_blocked": True,
        },
        "recommendation_policy": {
            "mode": "RESEARCH_ONLY",
            "agent_recommendations_authoritative": False,
            "tracker_recommendations_are_legacy_ui": True,
            "automatic_execution": False,
            "human_confirmation_required": True,
        },
        "wallets": wallet_inventory,
        "data_quality": {
            "daily_loss_guard_available": snapshot.daily_loss_guard_available,
            "unknown_custody_usd": exposure.unknown_custody_usd,
            "multi_source_unattributed_usd": exposure.multi_source_unattributed_usd,
            "unknown_liquidity_usd": exposure.unknown_liquidity_usd,
            "wallet_reconciliation_healthy": wallet_inventory["reconciliation_healthy"],
            "wallet_reconciliation_issue_count": wallet_inventory["reconciliation_issue_count"],
            "stale_wallet_count": wallet_inventory["stale_wallet_count"],
        },
        "assets": assets,
    }
