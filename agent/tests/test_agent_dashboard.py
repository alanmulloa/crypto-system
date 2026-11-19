from datetime import datetime, timezone

from app.config import Settings
from app.portfolio.dashboard import build_agent_dashboard
from app.portfolio.sync import TrackerPortfolioExport
from app.storage.portfolio_repository import InMemoryPortfolioSyncRepository


def export():
    return TrackerPortfolioExport(
        source_revision="v5.0.0",
        generated_at=datetime(2026, 11, 19, 12, tzinfo=timezone.utc),
        cartera_rows=[
            {
                "Activo": "BTC",
                "Cantidad actual": 0.02,
                "Valor actual USD": 1000,
                "Estado capital": "SOLO GANANCIAS",
                "Plataforma / Wallet": "Binance / Nexo",
            },
            {
                "Activo": "USDC",
                "Cantidad actual": 5000,
                "Valor actual USD": 5000,
                "Estado capital": "RESERVA",
                "Plataforma / Wallet": "Binance",
            },
        ],
        allocation_rows=[
            {
                "Activo": "BTC",
                "Peso objetivo %": 0.15,
                "Peso máximo %": 0.20,
            }
        ],
        reconciliation_rows=[
            {
                "Activo": "BTC",
                "Precio medio reconstruido": 18535.52,
                "Capital pendiente USD": 0,
                "Estado capital": "SOLO GANANCIAS",
                "Fuentes conciliadas": "Binance / Nexo",
            }
        ],
        daily_buy_used_usd=100,
    )


def test_dashboard_is_read_only_and_phase6_blocked():
    dashboard = build_agent_dashboard(
        export(),
        settings=Settings(
            kill_switch=True,
            max_daily_buy_usd=1000,
            min_cash_reserve_pct=25,
        ),
    )
    assert dashboard["summary"]["total_value_usd"] == 6000
    assert dashboard["summary"]["daily_buy_remaining_usd"] == 900
    assert dashboard["safety"]["operational_state"] == "SAFETY_LOCKED"
    assert dashboard["safety"]["phase6_eligible"] is False
    assert dashboard["safety"]["phase6_blocked"] is True
    assert dashboard["recommendation_policy"]["automatic_execution"] is False
    assert dashboard["assets"][0]["agent_recommendation"]["authoritative"] is False


def test_dashboard_exposes_portfolio_exposure_without_fake_custody_split():
    dashboard = build_agent_dashboard(
        export(),
        settings=Settings(kill_switch=True),
    )
    assert dashboard["exposure"]["multi_source_unattributed_usd"] == 1000
    assert dashboard["exposure"]["custody"][0]["source"] == "Binance"


def test_repository_can_return_latest_export():
    repository = InMemoryPortfolioSyncRepository()
    item = export()
    repository.save(item, item.to_snapshot(), item.content_hash())
    assert repository.latest_export("crypto_tracker") == item
    assert repository.latest_export("missing") is None
