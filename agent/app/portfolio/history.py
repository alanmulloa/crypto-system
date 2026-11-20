from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Sequence


def _dt(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _number(value: object) -> float:
    return float(value or 0.0)


def _nearest_before(
    rows: Sequence[Mapping[str, Any]],
    target: datetime,
) -> Mapping[str, Any] | None:
    eligible = [row for row in rows if _dt(row["generated_at"]) <= target]
    return eligible[-1] if eligible else None


def build_portfolio_history(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: _dt(row["generated_at"]))
    points = [
        {
            "generated_at": _dt(row["generated_at"]).isoformat(),
            "total_value_usd": _number(row.get("total_value_usd")),
            "cash_value_usd": _number(row.get("cash_value_usd")),
            "capital_at_risk_usd": _number(row.get("capital_at_risk_usd")),
            "content_hash": row.get("content_hash"),
        }
        for row in ordered
    ]
    if not points:
        return {
            "snapshot_count": 0,
            "latest_generated_at": None,
            "value_change": {},
            "points": [],
            "metric_semantics": {
                "value_change_is_investment_return": False,
                "reason": "No flow-adjustment is applied to deposits, withdrawals, buys or sells.",
            },
        }

    latest = points[-1]
    latest_dt = _dt(latest["generated_at"])
    windows = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    value_change: dict[str, Any] = {}
    for label, delta in windows.items():
        baseline = _nearest_before(points, latest_dt - delta)
        if baseline is None:
            value_change[label] = {
                "available": False,
                "absolute_usd": None,
                "pct": None,
                "baseline_generated_at": None,
            }
            continue
        start = _number(baseline["total_value_usd"])
        end = _number(latest["total_value_usd"])
        value_change[label] = {
            "available": True,
            "absolute_usd": end - start,
            "pct": ((end / start) - 1.0) * 100.0 if start > 0 else None,
            "baseline_generated_at": baseline["generated_at"],
        }

    return {
        "snapshot_count": len(points),
        "latest_generated_at": latest["generated_at"],
        "latest_total_value_usd": latest["total_value_usd"],
        "value_change": value_change,
        "points": points,
        "metric_semantics": {
            "value_change_is_investment_return": False,
            "reason": (
                "Portfolio snapshots are not flow-adjusted, so changes include "
                "market moves plus deposits, withdrawals and manual operations."
            ),
        },
    }
