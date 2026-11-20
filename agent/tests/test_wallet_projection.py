from datetime import datetime, timezone

from app.portfolio.wallet_projection import build_wallet_inventory


def test_wallet_inventory_masks_addresses_and_tracks_holdings():
    payload = build_wallet_inventory(
        wallet_rows=[
            {
                "Wallet": "MetaMask",
                "Red": "BSC",
                "Direccion publica": "0x1234567890abcdef",
                "Activa": "SI",
                "Ultima sync": "2026-11-19T10:00:00+00:00",
                "Estado": "OK",
            }
        ],
        onchain_rows=[
            {
                "Wallet": "MetaMask",
                "Red": "BSC",
                "Activo": "CAKE",
                "Disponible": 2,
                "Staking": 8,
                "Total on-chain": 10,
            }
        ],
        reconciliation_rows=[],
        as_of=datetime(2026, 11, 19, 12, tzinfo=timezone.utc),
    )
    assert payload["wallet_count"] == 1
    assert payload["active_wallet_count"] == 1
    assert payload["wallets"][0]["address"] == "0x1234…cdef"
    assert payload["wallets"][0]["holdings"][0]["asset"] == "CAKE"
    assert payload["wallets"][0]["freshness"] == "FRESH"


def test_wallet_inventory_flags_stale_and_reconciliation_issues():
    payload = build_wallet_inventory(
        wallet_rows=[
            {
                "Wallet": "Keplr",
                "Red": "Cosmos",
                "Activa": "SI",
                "Ultima sync": "2026-11-17T10:00:00+00:00",
            }
        ],
        onchain_rows=[],
        reconciliation_rows=[
            {
                "Activo": "ATOM",
                "Wallet/red": "Keplr/Cosmos",
                "Delta": 1.25,
                "Estado": "REVISAR",
            }
        ],
        as_of=datetime(2026, 11, 19, 12, tzinfo=timezone.utc),
    )
    assert payload["stale_wallet_count"] == 1
    assert payload["reconciliation_healthy"] is False
    assert payload["reconciliation_issue_count"] == 1
