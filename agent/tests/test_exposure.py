from app.portfolio import (
    CapitalState,
    LiquidityState,
    PortfolioPosition,
    PortfolioSnapshot,
    analyze_exposure,
    snapshot_from_tracker_rows,
)


def test_multi_custody_value_is_not_fake_split_between_sources():
    snapshot = PortfolioSnapshot(
        positions=(
            PortfolioPosition(
                "BTC",
                0.1,
                7000,
                capital_state=CapitalState.PROFITS_ONLY,
                custody_sources=("Binance", "Nexo"),
            ),
            PortfolioPosition(
                "DOT",
                10,
                300,
                capital_state=CapitalState.CAPITAL_AT_RISK,
                custody_sources=("Binance",),
            ),
            PortfolioPosition(
                "USDC",
                1000,
                1000,
                capital_state=CapitalState.CASH_RESERVE,
                custody_sources=("CoinDepo",),
                liquidity_state=LiquidityState.LIQUID,
            ),
        )
    )
    report = analyze_exposure(snapshot)
    known = {item.source: item.known_value_usd for item in report.custody}
    assert known == {"CoinDepo": 1000, "Binance": 300}
    assert report.multi_source_unattributed_usd == 7000


def test_liquidity_exposure_distinguishes_known_and_unknown():
    snapshot = PortfolioSnapshot(
        positions=(
            PortfolioPosition("CAKE", 10, 100, liquidity_state=LiquidityState.POOLED),
            PortfolioPosition("BTC", 0.1, 7000, liquidity_state=LiquidityState.LIQUID),
            PortfolioPosition("DOT", 10, 300, liquidity_state=LiquidityState.UNKNOWN),
        )
    )
    report = analyze_exposure(snapshot)
    assert report.explicit_illiquid_usd == 100
    assert report.known_liquid_usd == 7000
    assert report.unknown_liquidity_usd == 300


def test_tracker_position_type_can_infer_staking_without_hardcoding_asset():
    snapshot = snapshot_from_tracker_rows(
        cartera_rows=[
            {
                "Activo": "ATOM",
                "Cantidad actual": 10,
                "Valor actual USD": 100,
                "Tipo posición": "Staking",
            }
        ]
    )
    position = snapshot.position_for("ATOM")
    assert position is not None
    assert position.liquidity_state is LiquidityState.STAKED
    assert position.liquidity_basis == "position_type_inference"
