from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence


def _first(row: Mapping[str, object], *names: str) -> object | None:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return value
    return None


def _number(value: object | None) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _iso_datetime(value: object | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _masked_address(value: object | None) -> str | None:
    address = str(value or "").strip()
    if not address:
        return None
    if len(address) <= 12:
        return address
    return f"{address[:6]}…{address[-4:]}"


def build_wallet_inventory(
    *,
    wallet_rows: Sequence[Mapping[str, object]],
    onchain_rows: Sequence[Mapping[str, object]],
    reconciliation_rows: Sequence[Mapping[str, object]],
    as_of: datetime,
    stale_after_hours: int = 24,
) -> dict[str, Any]:
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=timezone.utc)
    else:
        as_of = as_of.astimezone(timezone.utc)

    holdings_by_wallet: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in onchain_rows:
        wallet = str(_first(row, "Wallet") or "").strip()
        network = str(_first(row, "Red", "Network") or "").strip()
        asset = str(_first(row, "Activo", "Asset") or "").strip().upper()
        if not wallet or not asset:
            continue
        holdings_by_wallet.setdefault((wallet, network), []).append(
            {
                "asset": asset,
                "available": _number(_first(row, "Disponible", "Available")),
                "staking": _number(_first(row, "Staking")),
                "rewards": _number(_first(row, "Rewards pendientes", "Rewards")),
                "total": _number(_first(row, "Total on-chain", "Total")),
                "source": str(_first(row, "Fuente", "Source") or "").strip() or None,
                "sync": str(_first(row, "Fecha sync", "Sync") or "").strip() or None,
                "note": str(_first(row, "Estado / notas", "Notas") or "").strip() or None,
            }
        )

    wallets = []
    networks: set[str] = set()
    active_count = 0
    stale_count = 0
    unknown_freshness_count = 0

    for row in wallet_rows:
        wallet = str(_first(row, "Wallet", "Nombre") or "").strip()
        if not wallet:
            continue
        network = str(_first(row, "Red", "Network") or "").strip()
        if network:
            networks.add(network)
        active_text = str(_first(row, "Activa", "Active") or "").strip().upper()
        active = active_text in {"SI", "SÍ", "YES", "TRUE", "1", "ACTIVA", "ACTIVE"}
        if active:
            active_count += 1

        sync_raw = _first(row, "Ultima sync", "Última sync", "Last sync")
        sync_dt = _iso_datetime(sync_raw)
        if sync_dt is None:
            freshness = "UNKNOWN"
            unknown_freshness_count += 1
            age_hours = None
        else:
            age_hours = max((as_of - sync_dt).total_seconds() / 3600.0, 0.0)
            freshness = "STALE" if age_hours > stale_after_hours else "FRESH"
            if freshness == "STALE":
                stale_count += 1

        holdings = holdings_by_wallet.get((wallet, network), [])
        wallets.append(
            {
                "wallet": wallet,
                "network": network or None,
                "address": _masked_address(
                    _first(row, "Direccion publica", "Dirección pública", "Address")
                ),
                "active": active,
                "status": str(_first(row, "Estado", "Status") or "").strip() or None,
                "last_sync": str(sync_raw or "").strip() or None,
                "freshness": freshness,
                "age_hours": age_hours,
                "holdings": holdings,
                "holding_count": len(holdings),
                "notes": str(_first(row, "Notas", "Notes") or "").strip() or None,
            }
        )

    issues = []
    for row in reconciliation_rows:
        asset = str(_first(row, "Activo", "Asset") or "").strip().upper()
        if not asset:
            continue
        status = str(_first(row, "Estado", "Status") or "").strip()
        normalized = status.upper()
        delta = _number(_first(row, "Delta"))
        ok = (
            normalized in {"OK", "SIN DIFERENCIA", "MATCHED", "CONCILIADO"}
            or abs(delta) < 1e-12
        )
        if not ok:
            issues.append(
                {
                    "asset": asset,
                    "wallet_network": str(
                        _first(row, "Wallet/red", "Wallet / red") or ""
                    ).strip()
                    or None,
                    "delta": delta,
                    "status": status or "REVIEW",
                    "notes": str(_first(row, "Notas", "Notes") or "").strip() or None,
                    "sync": str(
                        _first(row, "Ultima sync", "Última sync", "Sync") or ""
                    ).strip()
                    or None,
                }
            )

    return {
        "wallet_count": len(wallets),
        "active_wallet_count": active_count,
        "network_count": len(networks),
        "networks": sorted(networks),
        "stale_wallet_count": stale_count,
        "unknown_freshness_count": unknown_freshness_count,
        "reconciliation_issue_count": len(issues),
        "reconciliation_healthy": len(issues) == 0,
        "wallets": wallets,
        "reconciliation_issues": issues,
    }
