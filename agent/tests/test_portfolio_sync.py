from datetime import datetime, timedelta, timezone

from app.portfolio.sync import PortfolioSyncService, SyncState, TrackerPortfolioExport
from app.storage.portfolio_repository import InMemoryPortfolioSyncRepository


NOW = datetime(2026, 11, 10, 13, 0, tzinfo=timezone.utc)


def payload(*, generated_at=NOW, btc_value=1000):
    return TrackerPortfolioExport(
        source_revision="v2.9.0",
        generated_at=generated_at,
        cartera_rows=[
            {
                "Activo": "BTC",
                "Cantidad actual": 0.02,
                "Valor actual USD": btc_value,
                "Estado capital": "SOLO GANANCIAS",
            },
            {
                "Activo": "USDC",
                "Cantidad actual": 5000,
                "Valor actual USD": 5000,
                "Estado capital": "RESERVA",
            },
        ],
        allocation_rows=[
            {"Activo": "BTC", "Peso objetivo %": 0.15, "Peso máximo %": 0.20}
        ],
        reconciliation_rows=[
            {
                "Activo": "BTC",
                "Precio medio reconstruido": 18535.52,
                "Capital pendiente USD": 0,
                "Estado capital": "SOLO GANANCIAS",
            }
        ],
    )


def service(repository):
    return PortfolioSyncService(
        repository,
        max_age_minutes=30,
        now=lambda: NOW,
    )


def test_first_snapshot_is_applied_and_persisted():
    repository = InMemoryPortfolioSyncRepository()
    result = service(repository).sync(payload())
    assert result.state is SyncState.APPLIED
    assert len(repository.records) == 1
    assert result.total_value_usd == 6000
    assert result.cash_value_usd == 5000


def test_identical_snapshot_is_idempotent():
    repository = InMemoryPortfolioSyncRepository()
    svc = service(repository)
    first = svc.sync(payload())
    second = svc.sync(payload())
    assert first.state is SyncState.APPLIED
    assert second.state is SyncState.DUPLICATE
    assert first.content_hash == second.content_hash
    assert len(repository.records) == 1


def test_older_snapshot_is_rejected():
    repository = InMemoryPortfolioSyncRepository()
    svc = service(repository)
    assert svc.sync(payload(generated_at=NOW)).state is SyncState.APPLIED
    older = payload(generated_at=NOW - timedelta(minutes=1), btc_value=1200)
    result = svc.sync(older)
    assert result.state is SyncState.STALE
    assert len(repository.records) == 1


def test_snapshot_older_than_freshness_window_is_rejected():
    repository = InMemoryPortfolioSyncRepository()
    result = service(repository).sync(payload(generated_at=NOW - timedelta(minutes=31)))
    assert result.state is SyncState.STALE
    assert repository.records == []


def test_future_clock_skew_is_rejected():
    repository = InMemoryPortfolioSyncRepository()
    result = service(repository).sync(payload(generated_at=NOW + timedelta(minutes=6)))
    assert result.state is SyncState.STALE
    assert repository.records == []


def test_changed_newer_snapshot_gets_new_hash_and_is_applied():
    repository = InMemoryPortfolioSyncRepository()
    svc = service(repository)
    first = svc.sync(payload(generated_at=NOW - timedelta(minutes=2), btc_value=1000))
    second = svc.sync(payload(generated_at=NOW - timedelta(minutes=1), btc_value=1100))
    assert first.state is SyncState.APPLIED
    assert second.state is SyncState.APPLIED
    assert first.content_hash != second.content_hash
    assert len(repository.records) == 2
