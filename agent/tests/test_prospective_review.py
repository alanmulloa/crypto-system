import copy

from app.evaluation.prospective_collection import FROZEN_AT_MS
from app.evaluation.prospective_review import build_review


def report():
    return {
        "as_of_ms": FROZEN_AT_MS + 100_000,
        "baseline": {
            "cohort": "baseline",
            "observations": 0,
            "pending": 0,
            "matured": 0,
            "average_net_return_pct": None,
            "median_net_return_pct": None,
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
            "cohort": "candidate",
            "observations": 0,
            "pending": 0,
            "matured": 0,
            "average_net_return_pct": None,
            "median_net_return_pct": None,
            "positive_return_rate_pct": None,
        },
        "frozen_at_ms": FROZEN_AT_MS,
        "metadata": {
            "created_at": "2026-11-11T12:00:00+00:00",
            "phase": "5G-prospective",
            "public_binance_only": True,
            "research_only": True,
        },
        "min_matured_observations": 20,
        "observations": [],
        "outcome_hours": 24,
        "sample_ready": False,
        "uplift_vs_baseline_pct_points": None,
    }


def test_waits_for_first_candidate_signal():
    review = build_review(report())
    assert review["decision"] == "WAIT"
    assert review["state"] == "WAITING_FOR_CANDIDATE_SIGNAL"
    assert review["progress"]["percent"] == 0.0
    assert review["phase6_blocked"] is True


def test_waits_for_candidate_maturity():
    payload = report()
    payload["candidate_summary"].update(observations=1, pending=1)
    review = build_review(payload)
    assert review["state"] == "WAITING_FOR_MATURITY"
    assert review["milestones"]["first_candidate_observation"] is True
    assert review["milestones"]["first_candidate_matured"] is False


def test_accumulates_matured_sample_without_auto_promotion():
    payload = report()
    payload["candidate_summary"].update(
        observations=8,
        pending=3,
        matured=5,
        average_net_return_pct=0.4,
        median_net_return_pct=0.3,
        positive_return_rate_pct=60.0,
    )
    review = build_review(payload)
    assert review["decision"] == "WAIT"
    assert review["state"] == "ACCUMULATING_MATURED_SAMPLE"
    assert review["progress"]["percent"] == 25.0
    assert review["progress"]["remaining"] == 15
    assert review["guardrails"]["automatic_promotion"] is False


def test_sample_ready_requires_human_review_and_keeps_phase6_blocked():
    payload = report()
    payload["candidate_summary"].update(
        observations=22,
        pending=2,
        matured=20,
        average_net_return_pct=0.5,
        median_net_return_pct=0.4,
        positive_return_rate_pct=65.0,
    )
    payload["sample_ready"] = True
    payload["uplift_vs_baseline_pct_points"] = 0.25
    review = build_review(payload)
    assert review["decision"] == "REVIEW"
    assert review["state"] == "REVIEW_REQUIRED"
    assert review["progress"]["percent"] == 100.0
    assert review["phase6_blocked"] is True


def test_frozen_experiment_is_reported_unchanged():
    payload = report()
    review = build_review(copy.deepcopy(payload))
    assert review["frozen_experiment"] == {
        "symbol": "XRPUSDT",
        "feature": "volume_ratio_1h",
        "operator": "<=",
        "value": 0.75,
        "frozen_at_ms": FROZEN_AT_MS,
        "outcome_hours": 24,
    }
