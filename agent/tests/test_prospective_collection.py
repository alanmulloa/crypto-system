import copy
import json

import pytest

from app.evaluation.prospective_collection import (
    FROZEN_AT_MS,
    assert_history_compatible,
    collect,
    validate_report,
)


def report(*, observations=None):
    return {
        "as_of_ms": FROZEN_AT_MS + 10_000,
        "baseline": {
            "average_net_return_pct": None,
            "cohort": "baseline",
            "matured": 0,
            "median_net_return_pct": None,
            "observations": 0,
            "pending": 0,
            "positive_return_rate_pct": None,
        },
        "candidate": {
            "description": "XRPUSDT Mean Reversion WATCH BUY with 1h volume ratio <= 0.75",
            "feature": "volume_ratio_1h",
            "name": "xrp_low_volume_1h",
            "operator": "<=",
            "symbol": "XRPUSDT",
            "value": 0.75,
        },
        "candidate_summary": {
            "average_net_return_pct": None,
            "cohort": "candidate",
            "matured": 0,
            "median_net_return_pct": None,
            "observations": 0,
            "pending": 0,
            "positive_return_rate_pct": None,
        },
        "frozen_at_ms": FROZEN_AT_MS,
        "metadata": {
            "created_at": "2026-11-11T00:00:00+00:00",
            "phase": "5G-prospective",
            "public_binance_only": True,
            "research_only": True,
        },
        "min_matured_observations": 20,
        "observations": observations or [],
        "outcome_hours": 24,
        "sample_ready": False,
        "uplift_vs_baseline_pct_points": None,
    }


def pending(signal_offset=1):
    return {
        "cohort": "candidate",
        "symbol": "XRPUSDT",
        "signal_timestamp_ms": FROZEN_AT_MS + signal_offset,
        "entry_timestamp_ms": FROZEN_AT_MS + 3_600_000,
        "entry_market_price": 0.6,
        "feature_value": 0.5,
        "status": "PENDING",
        "outcome_timestamp_ms": FROZEN_AT_MS + 3_600_000 + 24 * 3_600_000,
        "gross_return_pct": None,
        "net_return_pct": None,
        "positive_return": None,
    }


def matured_from(item):
    result = copy.deepcopy(item)
    result["status"] = "MATURED"
    result["outcome_timestamp_ms"] = (
        result["entry_timestamp_ms"] + 24 * 3_600_000 - 1
    )
    result["gross_return_pct"] = 1.0
    result["net_return_pct"] = 0.7
    result["positive_return"] = True
    return result


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("frozen_at_ms",), FROZEN_AT_MS + 1, "frozen_at_ms changed"),
        (("candidate", "symbol"), "ETHUSDT", "candidate symbol changed"),
        (("candidate", "feature"), "rsi_1h", "candidate feature changed"),
        (("candidate", "operator"), ">=", "candidate operator changed"),
        (("candidate", "value"), 0.8, "candidate threshold changed"),
    ],
)
def test_frozen_candidate_invariants(path, value, message):
    payload = report()
    target = payload
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value

    with pytest.raises(ValueError, match=message):
        validate_report(payload)


def test_pre_freeze_observation_fails():
    item = pending()
    item["signal_timestamp_ms"] = FROZEN_AT_MS
    with pytest.raises(ValueError, match="strictly post-freeze"):
        validate_report(report(observations=[item]))


def test_matured_requires_full_24h_future():
    item = matured_from(pending())
    item["outcome_timestamp_ms"] = item["entry_timestamp_ms"] + 23 * 3_600_000
    with pytest.raises(ValueError, match="full 24h"):
        validate_report(report(observations=[item]))


def test_previous_observation_cannot_disappear():
    previous = report(observations=[pending()])
    current = report()
    with pytest.raises(ValueError, match="disappeared"):
        assert_history_compatible(previous, current)


def test_pending_may_transition_to_matured():
    old = pending()
    new = matured_from(old)
    assert_history_compatible(
        report(observations=[old]),
        report(observations=[new]),
    )


def test_matured_observation_cannot_mutate():
    old = matured_from(pending())
    new = copy.deepcopy(old)
    new["net_return_pct"] = 9.0
    with pytest.raises(ValueError, match="matured observation mutated"):
        assert_history_compatible(
            report(observations=[old]),
            report(observations=[new]),
        )


def test_collect_writes_latest_and_immutable_snapshot(tmp_path):
    fresh = tmp_path / "fresh.json"
    fresh.write_text(json.dumps(report()), encoding="utf-8")
    latest = tmp_path / "reports" / "phase5g" / "latest.json"
    history = tmp_path / "reports" / "phase5g" / "history"

    latest_path, snapshot_path = collect(
        fresh_report=fresh,
        latest_report=latest,
        history_dir=history,
    )

    assert latest_path.exists()
    assert snapshot_path.exists()
    assert json.loads(latest_path.read_text())["frozen_at_ms"] == FROZEN_AT_MS
