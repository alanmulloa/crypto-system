from datetime import datetime, timezone

from app.config import Settings
from app.portfolio.dashboard import build_agent_dashboard
from app.portfolio.sync import TrackerPortfolioExport


def test_dashboard_includes_wallet_health_and_reconciliation():
    export = TrackerPortfolioExport(
        schema_version="1.1",
        source_revision="v5.1.0",
        generated_at=datetime(2026, 11, 19, 12, tzinfo=timezone.utc),
        cartera_rows=[
            {
                "Activo": "USDC",
                "Cantidad actual": 1000,
                "Valor actual USD": 1000,
                "Estado capital": "RESERVA",
            }
        ],
        wallet_rows=[
            {
                "Wallet": "MetaMask",
                "Red": "BSC",
                "Direccion publica": "0x1234567890abcdef",
                "Activa": "SI",
                "Ultima sync": "2026-11-19T11:00:00+00:00",
            }
        ],
        onchain_rows=[
            {
                "Wallet": "MetaMask",
                "Red": "BSC",
                "Activo": "CAKE",
                "Total on-chain": 10,
            }
        ],
        onchain_reconciliation_rows=[
            {
                "Activo": "CAKE",
                "Wallet/red": "MetaMask/BSC",
                "Delta": 2,
                "Estado": "REVISAR",
            }
        ],
    )
    dashboard = build_agent_dashboard(export, settings=Settings())
    assert dashboard["wallets"]["wallet_count"] == 1
    assert dashboard["wallets"]["wallets"][0]["address"] == "0x1234…cdef"
    assert dashboard["wallets"]["reconciliation_issue_count"] == 1
    assert dashboard["data_quality"]["wallet_reconciliation_healthy"] is False
    assert dashboard["safety"]["phase6_blocked"] is True
