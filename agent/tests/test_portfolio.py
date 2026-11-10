from app.portfolio import (
    CapitalState,
    PortfolioPosition,
    PortfolioSnapshot,
    normalize_capital_state,
    snapshot_from_tracker_rows,
)


def test_tracker_capital_states_are_normalized():
    assert normalize_capital_state("SOLO GANANCIAS", asset="BTC") is CapitalState.PROFITS_ONLY
    assert normalize_capital_state("capital en riesgo", asset="DOT") is CapitalState.CAPITAL_AT_RISK
    assert normalize_capital_state("", asset="USDC") is CapitalState.CASH_RESERVE


def test_tracker_rows_build_snapshot_without_creating_second_portfolio_model():
    snapshot = snapshot_from_tracker_rows(
        cartera_rows=[
            {
                "Activo": "BTC",
                "Cantidad actual": 0.1,
                "Valor actual USD": 7000,
                "Estado capital": "SOLO GANANCIAS",
                "Tipo posición": "Core",
            },
            {
                "Activo": "USDC",
                "Cantidad actual": 5000,
                "Valor actual USD": 5000,
                "Estado capital": "RESERVA",
            },
        ],
        reconciliation_rows=[
            {
                "Activo": "BTC",
                "Precio medio reconstruido": 18535.52,
                "Capital pendiente USD": 0,
                "Estado capital": "SOLO GANANCIAS",
                "Fuentes conciliadas": "Binance / Nexo / YouHodler",
            }
        ],
        allocation_rows=[
            {"Activo": "BTC", "Peso objetivo %": 0.15, "Peso máximo %": 0.20, "Prioridad": "Alta"}
        ],
    )
    btc = snapshot.position_for("BTC")
    assert btc is not None
    assert btc.avg_cost_usd == 18535.52
    assert btc.capital_state is CapitalState.PROFITS_ONLY
    assert btc.custody_sources == ("Binance", "Nexo", "YouHodler")
    assert snapshot.allocation_for("BTC").max_weight_pct == 20
    assert snapshot.cash_value_usd == 5000


def test_profits_only_is_not_counted_as_pending_capital_at_risk():
    snapshot = PortfolioSnapshot(
        positions=(
            PortfolioPosition("BTC", 0.1, 7000, capital_state=CapitalState.PROFITS_ONLY),
            PortfolioPosition(
                "DOT",
                10,
                300,
                capital_pending_usd=180,
                capital_state=CapitalState.CAPITAL_AT_RISK,
            ),
            PortfolioPosition("USDC", 1000, 1000, capital_state=CapitalState.CASH_RESERVE),
        )
    )
    assert snapshot.capital_at_risk_usd == 180
