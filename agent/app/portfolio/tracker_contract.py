from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.portfolio.models import AllocationTarget, CapitalState, PortfolioPosition, PortfolioSnapshot


_CAPITAL_STATE_MAP = {
    "SOLO GANANCIAS": CapitalState.PROFITS_ONLY,
    "CAPITAL EN RIESGO": CapitalState.CAPITAL_AT_RISK,
    "CAPITAL RECUPERADO / REVISAR": CapitalState.RECOVERED_REVIEW,
    "CAPITAL EN RIESGO - RECONSTRUCCION PARCIAL": CapitalState.PARTIAL_RECONSTRUCTION,
    "RESERVA": CapitalState.CASH_RESERVE,
}


def normalize_capital_state(value: str | None, *, asset: str | None = None, cash_asset: str = "USDC") -> CapitalState:
    if asset and asset.upper() == cash_asset.upper():
        return CapitalState.CASH_RESERVE
    normalized = " ".join(str(value or "").strip().upper().split())
    return _CAPITAL_STATE_MAP.get(normalized, CapitalState.UNKNOWN)


def _number(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid numeric value: {value!r}") from exc


def _sources(value: object) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(
        part.strip()
        for part in str(value).split("/")
        if part.strip()
    )


def snapshot_from_tracker_rows(
    *,
    cartera_rows: Sequence[Mapping[str, object]],
    allocation_rows: Sequence[Mapping[str, object]] = (),
    reconciliation_rows: Sequence[Mapping[str, object]] = (),
    cash_asset: str = "USDC",
    daily_buy_used_usd: float = 0.0,
    daily_realized_pnl_usd: float = 0.0,
) -> PortfolioSnapshot:
    reconciliation = {
        str(row.get("Activo") or "").strip().upper(): row
        for row in reconciliation_rows
        if str(row.get("Activo") or "").strip()
    }

    positions: list[PortfolioPosition] = []
    for row in cartera_rows:
        asset = str(row.get("Activo") or "").strip().upper()
        if not asset:
            continue
        rec = reconciliation.get(asset, {})

        quantity = _number(row.get("Cantidad actual"))
        if quantity is None:
            quantity = _number(row.get("Cantidad")) or 0.0

        market_value = _number(row.get("Valor actual USD"))
        if market_value is None:
            market_value = _number(row.get("Valor USD")) or 0.0

        state_value = row.get("Estado capital") or rec.get("Estado capital")
        sources_value = rec.get("Fuentes conciliadas") or row.get("Plataforma / Wallet") or row.get("Origen")

        avg_cost = _number(rec.get("Precio medio reconstruido"))
        capital_pending = _number(rec.get("Capital pendiente USD"))

        positions.append(
            PortfolioPosition(
                asset=asset,
                quantity=quantity,
                market_value_usd=market_value,
                avg_cost_usd=avg_cost,
                capital_pending_usd=capital_pending,
                capital_state=normalize_capital_state(state_value, asset=asset, cash_asset=cash_asset),
                custody_sources=_sources(sources_value),
                position_type=(str(row.get("Tipo posición") or "").strip() or None),
            )
        )

    allocations: list[AllocationTarget] = []
    for row in allocation_rows:
        asset = str(row.get("Activo") or "").strip().upper()
        if not asset:
            continue
        target = _number(row.get("Peso objetivo %"))
        maximum = _number(row.get("Peso máximo %"))

        # Tracker stores percentages as Sheets fractions (e.g. 0.20 == 20%).
        if target is not None and 0 <= target <= 1:
            target *= 100
        if maximum is not None and 0 <= maximum <= 1:
            maximum *= 100

        allocations.append(
            AllocationTarget(
                asset=asset,
                target_weight_pct=target,
                max_weight_pct=maximum,
                priority=(str(row.get("Prioridad") or "").strip() or None),
            )
        )

    return PortfolioSnapshot(
        positions=tuple(positions),
        allocations=tuple(allocations),
        cash_asset=cash_asset,
        daily_buy_used_usd=daily_buy_used_usd,
        daily_realized_pnl_usd=daily_realized_pnl_usd,
    )
