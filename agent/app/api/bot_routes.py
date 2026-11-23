from __future__ import annotations

import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query, status

from app.config import get_settings
from app.decision.journal import DecisionJournal


router = APIRouter(prefix="/bot", tags=["bot"])


def _bearer_token(authorization: str | None) -> str:
    if not authorization:
        return ""
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return ""
    return token.strip()


def _require_auth(settings, authorization: str | None) -> None:
    """Verify bearer token for bot endpoints."""
    if not settings.bot_api_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="bot API is disabled",
        )
    token = _bearer_token(authorization)
    if not token or not hmac.compare_digest(token, settings.bot_api_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid bot API token",
        )


def _supabase_client(settings):
    """Create a simple Supabase REST client for queries."""
    import urllib.request
    import json
    from urllib.parse import urlencode

    class SupabaseClient:
        def __init__(self, url: str, key: str):
            self.url = url.rstrip("/")
            self.key = key
            self.headers = {
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            }

        def select(
            self,
            table: str,
            columns: str = "*",
            filters: dict[str, str] | None = None,
            order: str | None = None,
            limit: int | None = None,
        ) -> list[dict[str, Any]]:
            params = {"select": columns}
            if filters:
                params.update(filters)
            if order:
                params["order"] = order
            if limit:
                params["limit"] = str(limit)

            query = urlencode(params)
            req = urllib.request.Request(
                f"{self.url}/rest/v1/{table}?{query}",
                headers=self.headers,
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=10) as response:  # noqa: S310
                return json.loads(response.read().decode("utf-8"))

        def select_one(
            self,
            table: str,
            columns: str = "*",
            filters: dict[str, str] | None = None,
        ) -> dict[str, Any] | None:
            rows = self.select(table, columns, filters, limit=1)
            return rows[0] if rows else None

    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="bot API storage is not configured",
        )
    return SupabaseClient(settings.supabase_url, settings.supabase_service_role_key)


@router.get("/activity")
def bot_activity(
    authorization: str | None = Header(default=None),
    symbol: str | None = Query(default=None, description="Filter by symbol (e.g., BTCUSDT)"),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum number of opportunities to return"),
    since_hours: int | None = Query(default=None, ge=1, le=720, description="Filter to last N hours"),
):
    """Get complete bot activity trace: Opportunity → Decision → Order → Fill → Trade."""
    settings = get_settings()
    _require_auth(settings, authorization)

    client = _supabase_client(settings)

    # Build filters for opportunities
    filters: dict[str, str] = {}
    if symbol:
        filters["symbol"] = f"eq.{symbol.upper()}"
    if since_hours:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).isoformat()
        filters["created_at"] = f"gte.{cutoff}"

    # Fetch opportunities with related data using the view
    try:
        # Use the bot_activity_trace view for complete trace
        rows = client.select(
            "bot_activity_trace",
            columns="*",
            filters=filters,
            order="opportunity_created_at.desc",
            limit=limit,
        )
    except Exception:
        # Fallback: manual join if view doesn't exist yet
        rows = _manual_activity_trace(client, filters, limit)

    # Group by opportunity for cleaner response
    by_opportunity: dict[str, dict[str, Any]] = {}
    for row in rows:
        opp_id = str(row.get("opportunity_id") or "")
        if not opp_id:
            continue
        if opp_id not in by_opportunity:
            by_opportunity[opp_id] = {
                "opportunity": {
                    "id": opp_id,
                    "symbol": row.get("symbol"),
                    "strategy": row.get("opportunity_strategy"),
                    "direction": row.get("opportunity_direction"),
                    "score": row.get("opportunity_score"),
                    "confidence": row.get("opportunity_confidence"),
                    "created_at": row.get("opportunity_created_at"),
                },
                "decisions": [],
                "orders": [],
                "fills": [],
                "trades": [],
            }

        # Decision
        decision_id = row.get("decision_id")
        if decision_id and not any(d["id"] == decision_id for d in by_opportunity[opp_id]["decisions"]):
            by_opportunity[opp_id]["decisions"].append({
                "id": str(decision_id),
                "action": row.get("decision_action"),
                "status": row.get("decision_status"),
                "risk_approved": row.get("risk_approved"),
                "max_notional_usd": row.get("max_notional_usd"),
                "created_at": row.get("decision_created_at"),
            })

        # Order
        order_id = row.get("order_id")
        if order_id and not any(o["id"] == order_id for o in by_opportunity[opp_id]["orders"]):
            by_opportunity[opp_id]["orders"].append({
                "id": str(order_id),
                "symbol": row.get("order_symbol"),
                "side": row.get("order_side"),
                "order_type": row.get("order_type"),
                "quantity": row.get("order_quantity"),
                "notional_usd": row.get("order_notional_usd"),
                "limit_price": row.get("order_limit_price"),
                "status": row.get("order_status"),
                "execution_price": row.get("execution_price"),
                "execution_quantity": row.get("execution_quantity"),
                "execution_fee_usd": row.get("execution_fee_usd"),
                "execution_timestamp": row.get("execution_timestamp"),
                "created_at": row.get("order_created_at"),
            })

        # Fill
        fill_id = row.get("fill_id")
        if fill_id and not any(f["id"] == fill_id for f in by_opportunity[opp_id]["fills"]):
            by_opportunity[opp_id]["fills"].append({
                "id": str(fill_id),
                "price": row.get("fill_price"),
                "quantity": row.get("fill_quantity"),
                "fee_usd": row.get("fill_fee_usd"),
                "realized_pnl_usd": row.get("fill_realized_pnl_usd"),
                "filled_at": row.get("filled_at"),
            })

        # Trade
        trade_id = row.get("trade_id")
        if trade_id and not any(t["id"] == trade_id for t in by_opportunity[opp_id]["trades"]):
            by_opportunity[opp_id]["trades"].append({
                "id": str(trade_id),
                "strategy": row.get("trade_strategy"),
                "opened_at": row.get("opened_at"),
                "closed_at": row.get("closed_at"),
                "entry_price": row.get("entry_price"),
                "exit_price": row.get("exit_price"),
                "quantity": row.get("trade_quantity"),
                "pnl_usd": row.get("trade_pnl_usd"),
                "pnl_pct": row.get("trade_pnl_pct"),
                "realized_pnl_usd": row.get("trade_realized_pnl_usd"),
                "market_regime": row.get("trade_market_regime"),
            })

    return {
        "total": len(by_opportunity),
        "activities": list(by_opportunity.values()),
    }


def _manual_activity_trace(client, filters: dict[str, str], limit: int) -> list[dict[str, Any]]:
    """Manual join fallback if bot_activity_trace view is not available."""
    # Fetch opportunities
    opp_filters = filters.copy()
    opportunities = client.select(
        "opportunities",
        columns="id,symbol,strategy,direction,score,confidence,created_at",
        filters=opp_filters,
        order="created_at.desc",
        limit=limit,
    )

    results = []
    for opp in opportunities:
        opp_id = str(opp["id"])
        # Decisions
        decisions = client.select(
            "decisions",
            columns="id,opportunity_id,decision,decision_status,risk_approved,max_notional_usd,created_at",
            filters={"opportunity_id": f"eq.{opp_id}"},
        )
        for dec in decisions:
            dec_id = str(dec["id"])
            # Orders
            orders = client.select(
                "orders",
                columns="id,decision_id,symbol,side,order_type,quantity,notional_usd,limit_price,status,execution_price,execution_quantity,execution_fee_usd,execution_timestamp,created_at,raw",
                filters={"decision_id": f"eq.{dec_id}"},
            )
            for ord_ in orders:
                ord_id = str(ord_["id"])
                # Fills
                fills = client.select(
                    "fills",
                    columns="id,order_id,price,quantity,fee_usd,realized_pnl_usd,filled_at,raw",
                    filters={"order_id": f"eq.{ord_id}"},
                )
                # Trades (via order_id if available)
                trades = client.select(
                    "trades",
                    columns="id,strategy,opened_at,closed_at,entry_price,exit_price,quantity,pnl_usd,pnl_pct,realized_pnl_usd,market_regime,metadata",
                    filters={"order_id": f"eq.{ord_id}"},
                )
                # Merge into result
                for fill in fills:
                    for trade in trades:
                        results.append({**opp, **dec, **ord_, **fill, **trade})
                if not fills:
                    for trade in trades:
                        results.append({**opp, **dec, **ord_, **trade})
                if not trades:
                    for fill in fills:
                        results.append({**opp, **dec, **ord_, **fill})
                    if not fills:
                        results.append({**opp, **dec, **ord_})
            if not orders:
                for dec in decisions:
                    results.append({**opp, **dec})
    return results


@router.get("/paper-portfolio")
def bot_paper_portfolio(
    authorization: str | None = Header(default=None),
):
    """Get paper portfolio positions with unrealized/realized PnL."""
    settings = get_settings()
    _require_auth(settings, authorization)

    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="bot API storage is not configured",
        )

    # Use the paper broker's in-memory state via the orchestrator/repository
    # For now, query from paper execution orders/fills in Supabase
    client = _supabase_client(settings)

    # Get all paper orders that are filled (kept for potential future use)
    _orders = client.select(
        "orders",
        columns="id,symbol,side,quantity,notional_usd,status,execution_price,execution_quantity,execution_fee_usd,created_at,raw",
        filters={"broker": "eq.PAPER", "status": "eq.FILLED"},
        order="created_at.desc",
    )

    # Get fills for realized PnL - symbol/side are in raw JSONB, not as columns
    fills = client.select(
        "fills",
        columns="order_id,price,quantity,fee_usd,realized_pnl_usd,filled_at,raw",
    )

    # Build position map from fills
    positions: dict[str, dict[str, Any]] = {}
    realized_pnl_by_symbol: dict[str, float] = {}
    fees_by_symbol: dict[str, float] = {}

    for fill in fills:
        # Extract symbol and side from raw JSONB
        raw = fill.get("raw") or {}
        symbol = (raw.get("symbol") or "").upper()
        if not symbol:
            continue
        side = raw.get("side") or "BUY"
        qty = float(fill.get("quantity") or 0)
        price = float(fill.get("price") or 0)
        fee = float(fill.get("fee_usd") or 0)
        realized = float(fill.get("realized_pnl_usd") or 0)

        if symbol not in positions:
            positions[symbol] = {"quantity": 0.0, "avg_cost": 0.0, "total_cost": 0.0}

        pos = positions[symbol]
        if side == "BUY":
            new_total_cost = pos["total_cost"] + qty * price + fee
            new_qty = pos["quantity"] + qty
            pos["avg_cost"] = new_total_cost / new_qty if new_qty > 0 else 0
            pos["total_cost"] = new_total_cost
            pos["quantity"] = new_qty
        elif side == "SELL":
            pos["quantity"] = max(0.0, pos["quantity"] - qty)
            if pos["quantity"] <= 0:
                pos["quantity"] = 0.0
                pos["avg_cost"] = 0.0
                pos["total_cost"] = 0.0

        realized_pnl_by_symbol[symbol] = realized_pnl_by_symbol.get(symbol, 0.0) + realized
        fees_by_symbol[symbol] = fees_by_symbol.get(symbol, 0.0) + fee

    # Build response - NO current price proxy; return null with PRICE_UNAVAILABLE
    portfolio = []
    _total_unrealized = 0.0
    total_realized = 0.0

    for symbol, pos in positions.items():
        if pos["quantity"] <= 0:
            continue
        # We don't have a reliable current market price
        # Return null for price and unrealized PnL with status indicator
        _market_value = None
        _unrealized = None

        total_realized += realized_pnl_by_symbol.get(symbol, 0.0)

        portfolio.append({
            "symbol": symbol,
            "quantity": pos["quantity"],
            "avg_cost_usd": pos["avg_cost"],
            "current_price_usd": None,
            "market_value_usd": None,
            "unrealized_pnl_usd": None,
            "unrealized_pnl_status": "PRICE_UNAVAILABLE",
            "realized_pnl_usd": realized_pnl_by_symbol.get(symbol, 0.0),
            "total_pnl_usd": None,  # Can't compute without current price
            "fees_usd": fees_by_symbol.get(symbol, 0.0),
        })

    # Add cash from paper broker account (would need broker state)
    # For now, we can't access it directly - return what we have

    return {
        "positions": portfolio,
        "summary": {
            "total_unrealized_pnl_usd": None,
            "total_unrealized_pnl_status": "PRICE_UNAVAILABLE",
            "total_realized_pnl_usd": round(total_realized, 2),
            "total_pnl_usd": None,
            "position_count": len(portfolio),
        },
    }


@router.get("/performance")
def bot_performance(
    authorization: str | None = Header(default=None),
    days: int = Query(default=30, ge=1, le=365, description="Lookback period in days"),
):
    """Get bot performance metrics over the specified period."""
    settings = get_settings()
    _require_auth(settings, authorization)

    client = _supabase_client(settings)

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    # Get trades in period (real trading round-trips)
    trades = client.select(
        "trades",
        columns="id,symbol,strategy,opened_at,closed_at,entry_price,exit_price,quantity,pnl_usd,pnl_pct,realized_pnl_usd,market_regime,metadata",
        filters={"closed_at": f"gte.{cutoff}"},
        order="closed_at.desc",
    )

    # Get fills in period for PAPER TRADING ONLY
    # (fills for real trading are part of trades, so we filter by broker=PAPER)
    fills = client.select(
        "fills",
        columns="order_id,price,quantity,fee_usd,realized_pnl_usd,filled_at,raw",
        filters={"filled_at": f"gte.{cutoff}"},
    )

    # Filter fills to only paper trading (broker in raw)
    paper_fills = [f for f in fills if (f.get("raw") or {}).get("broker") == "PAPER"]

    # Calculate metrics for REAL TRADING (from trades)
    real_trades = [t for t in trades if (t.get("metadata") or {}).get("broker") != "PAPER"]
    total_trades = len(real_trades)
    winning_trades = sum(1 for t in real_trades if float(t.get("pnl_usd") or 0) > 0)
    losing_trades = sum(1 for t in real_trades if float(t.get("pnl_usd") or 0) < 0)
    real_pnl = sum(float(t.get("pnl_usd") or 0) for t in real_trades)

    # Paper trading PnL from fills (not double-counted with trades)
    paper_pnl = sum(float(f.get("realized_pnl_usd") or 0) for f in paper_fills)
    paper_fees = sum(float(f.get("fee_usd") or 0) for f in paper_fills)

    # Total PnL = real trades PnL + paper fills PnL (NO double counting)
    total_pnl = real_pnl + paper_pnl
    total_fees = paper_fees  # real trades fees are embedded in pnl_usd

    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

    # Group by strategy (real trades only)
    by_strategy: dict[str, dict[str, Any]] = {}
    for trade in real_trades:
        strat = trade.get("strategy") or "unknown"
        if strat not in by_strategy:
            by_strategy[strat] = {"trades": 0, "wins": 0, "pnl_usd": 0.0}
        by_strategy[strat]["trades"] += 1
        pnl = float(trade.get("pnl_usd") or 0)
        by_strategy[strat]["pnl_usd"] += pnl
        if pnl > 0:
            by_strategy[strat]["wins"] += 1

    # Group by symbol (real trades only)
    by_symbol: dict[str, dict[str, Any]] = {}
    for trade in real_trades:
        sym = trade.get("symbol", "unknown")
        if sym not in by_symbol:
            by_symbol[sym] = {"trades": 0, "pnl_usd": 0.0}
        by_symbol[sym]["trades"] += 1
        by_symbol[sym]["pnl_usd"] += float(trade.get("pnl_usd") or 0)

    # Paper trading breakdown
    paper_by_symbol: dict[str, dict[str, Any]] = {}
    for fill in paper_fills:
        if float(fill.get("realized_pnl_usd") or 0) == 0:
            continue
        # Extract symbol from raw
        raw = fill.get("raw") or {}
        sym = (raw.get("symbol") or "unknown").upper()
        if sym not in paper_by_symbol:
            paper_by_symbol[sym] = {"trades": 0, "pnl_usd": 0.0}
        paper_by_symbol[sym]["trades"] += 1
        paper_by_symbol[sym]["pnl_usd"] += float(fill.get("realized_pnl_usd") or 0)

    return {
        "period_days": days,
        "summary": {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate_pct": round(win_rate, 2),
            "total_pnl_usd": round(total_pnl, 2),
            "total_fees_usd": round(total_fees, 2),
            "net_pnl_usd": round(total_pnl - total_fees, 2),
        },
        "by_strategy": {
            k: {
                "trades": v["trades"],
                "wins": v["wins"],
                "win_rate_pct": round(v["wins"] / v["trades"] * 100, 2) if v["trades"] > 0 else 0,
                "pnl_usd": round(v["pnl_usd"], 2),
            }
            for k, v in by_strategy.items()
        },
        "by_symbol": {
            k: {"trades": v["trades"], "pnl_usd": round(v["pnl_usd"], 2)}
            for k, v in by_symbol.items()
        },
        "paper_trading": {
            "by_symbol": {
                k: {"trades": v["trades"], "pnl_usd": round(v["pnl_usd"], 2)}
                for k, v in paper_by_symbol.items()
            },
            "total_pnl_usd": round(paper_pnl, 2),
            "total_fees_usd": round(paper_fees, 2),
        },
    }


@router.get("/decisions")
def bot_decisions(
    authorization: str | None = Header(default=None),
    cycle_id: str | None = Query(default=None, description="Filter by cycle ID"),
    symbol: str | None = Query(default=None, description="Filter by symbol"),
    action: str | None = Query(default=None, description="Filter by action (BUY/SELL/REDUCE/NO_ACTION)"),
    eligibility: str | None = Query(default=None, description="Filter by eligibility (RESEARCH_ONLY/BLOCKED/PAPER_PROPOSAL)"),
    limit: int = Query(default=100, ge=1, le=500, description="Maximum number of decisions to return"),
    since_hours: int | None = Query(default=None, ge=1, le=720, description="Filter to last N hours"),
):
    """Get decision journal entries with optional filters."""
    settings = get_settings()
    _require_auth(settings, authorization)

    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="bot API storage is not configured",
        )

    journal = DecisionJournal(settings)

    decisions = journal.get_recent_decisions(
        limit=limit,
        symbol=symbol.upper() if symbol else None,
        action=action,
    )

    # Apply additional filters
    if cycle_id:
        decisions = [d for d in decisions if d.cycle_id == cycle_id]
    if eligibility:
        decisions = [d for d in decisions if d.eligibility == eligibility]
    if since_hours:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
        decisions = [d for d in decisions if d.timestamp >= cutoff]

    # Apply limit after filtering
    decisions = decisions[:limit]

    # Include outcomes for each decision
    result = []
    for d in decisions:
        entry = {
            "decision_id": d.decision_id,
            "cycle_id": d.cycle_id,
            "timestamp": d.timestamp.isoformat(),
            "symbol": d.symbol,
            "action": d.action,
            "eligibility": d.eligibility,
            "confidence_score": d.confidence_score,
            "heuristic_score": d.heuristic_score,
            "risk_state": d.risk_state,
            "aggregate_state": d.aggregate_state,
            "direction": d.direction,
            "max_notional_usd": d.max_notional_usd,
        }
        if d.entry_plan_json:
            entry["entry_plan"] = json.loads(d.entry_plan_json)
        if d.reasons_json:
            entry["reasons"] = json.loads(d.reasons_json)
        if d.warnings_json:
            entry["warnings"] = json.loads(d.warnings_json)
        if d.sizing_details_json:
            entry["sizing_details"] = json.loads(d.sizing_details_json)

        # Fetch outcomes
        outcomes = journal.get_outcomes_for_decision(d.decision_id)
        if outcomes:
            entry["outcomes"] = [
                {
                    "order_id": o.order_id,
                    "filled": o.filled,
                    "fill_price": o.fill_price,
                    "quantity": o.quantity,
                    "notional": o.notional,
                    "fees_usd": o.fees_usd,
                    "slippage_usd": o.slippage_usd,
                    "pnl_usd": o.pnl_usd,
                    "timestamp": o.timestamp.isoformat(),
                }
                for o in outcomes
            ]

        result.append(entry)

    return {
        "total": len(result),
        "decisions": result,
    }


@router.get("/decisions/stats")
def bot_decisions_stats(
    authorization: str | None = Header(default=None),
    since_hours: int = Query(default=168, ge=1, le=720, description="Lookback period in hours (default 7 days)"),
):
    """Get aggregated decision journal statistics."""
    settings = get_settings()
    _require_auth(settings, authorization)

    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="bot API storage is not configured",
        )

    journal = DecisionJournal(settings)
    stats = journal.get_performance_stats(since_hours=since_hours)

    return stats