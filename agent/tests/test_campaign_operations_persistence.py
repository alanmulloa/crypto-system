import json

import pytest

from app.evaluation.campaign_incidents import detect_campaign_incidents
from app.evaluation.campaign_operations_persistence import (
    persist_campaign_operations,
)


def report(timestamp="2026-11-20T00:00:00+00:00"):
    return {
        "phase": "5L.5",
        "generated_at": timestamp,
        "campaign_fingerprint_sha256": "a" * 64,
        "data_health": {
            "all_symbols_healthy": True,
            "symbols": [],
        },
        "screening_readiness": {
            "fingerprint_matches": True,
        },
        "research_only": True,
        "phase6_blocked": True,
    }


def test_persistence_is_append_only(tmp_path):
    fresh = tmp_path / "fresh.json"
    latest = tmp_path / "latest.json"
    history = tmp_path / "history"
    fresh.write_text(json.dumps(report()), encoding="utf-8")
    _, snapshot = persist_campaign_operations(
        fresh_report=fresh,
        latest_report=latest,
        history_dir=history,
    )
    assert latest.exists()
    assert snapshot.exists()


def test_persistence_rejects_fingerprint_drift(tmp_path):
    fresh = tmp_path / "fresh.json"
    latest = tmp_path / "latest.json"
    history = tmp_path / "history"
    latest.write_text(json.dumps(report()), encoding="utf-8")
    changed = report("2026-11-21T00:00:00+00:00")
    changed["campaign_fingerprint_sha256"] = "b" * 64
    fresh.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError, match="fingerprint drift"):
        persist_campaign_operations(
            fresh_report=fresh,
            latest_report=latest,
            history_dir=history,
        )


def test_incident_detector_flags_unhealthy_data():
    payload = report()
    payload["data_health"] = {
        "all_symbols_healthy": False,
        "symbols": [
            {
                "symbol": "BTCUSDT",
                "spot_available": True,
                "intervals": [
                    {
                        "interval": "1h",
                        "gap_count": 1,
                        "duplicate_open_times": 0,
                        "fresh": False,
                    }
                ],
            }
        ],
    }
    incidents = detect_campaign_incidents(payload)
    codes = {item.code for item in incidents}
    assert "MARKET_DATA_UNHEALTHY" in codes
    assert "INTERVAL_GAP" in codes
    assert "STALE_CANDLES" in codes
