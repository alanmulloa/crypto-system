import copy

from app.evaluation.prospective_collection import FROZEN_AT_MS
from app.evaluation.prospective_decision import build_decision


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
            "created_at": "2026-11-11T15:30:00+00:00",
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


def ready_report():
    payload = report()
    payload["candidate_summary"].update(
        observations=20,
        pending=0,
        matured=20,
        average_net_return_pct=0.4,
        median_net_return_pct=0.2,
        positive_return_rate_pct=60.0,
    )
    payload["baseline"].update(
        observations=20,
        pending=0,
        matured=20,
        average_net_return_pct=0.1,
        median_net_return_pct=0.05,
        positive_return_rate_pct=55.0,
    )
    payload["sample_ready"] = True
    payload["uplift_vs_baseline_pct_points"] = 0.3
    return payload


def test_not_ready_before_minimum_matured_sample():
    decision = build_decision(report())
    assert decision["decision"] == "NOT_READY"
    assert decision["phase6_eligible"] is False
    assert decision["phase6_blocked"] is True


def test_pass_research_when_all_preregistered_metrics_pass():
    decision = build_decision(ready_report())
    assert decision["decision"] == "PASS_RESEARCH"
    assert decision["research_gate_passed"] is True
    assert decision["phase6_eligible"] is False
    assert decision["guardrails"]["automatic_phase6_promotion"] is False


def test_fail_research_when_one_metric_fails():
    payload = ready_report()
    payload["candidate_summary"]["median_net_return_pct"] = -0.01
    decision = build_decision(payload)
    assert decision["decision"] == "FAIL_RESEARCH"
    assert decision["criteria"]["median_net_return_positive"] is False
    assert decision["research_gate_passed"] is False


def test_exactly_50_percent_positive_rate_fails_strict_threshold():
    payload = ready_report()
    payload["candidate_summary"]["positive_return_rate_pct"] = 50.0
    decision = build_decision(payload)
    assert decision["decision"] == "FAIL_RESEARCH"
    assert decision["criteria"]["positive_return_rate_above_50"] is False


def test_inconclusive_when_ready_sample_has_missing_metric():
    payload = ready_report()
    payload["uplift_vs_baseline_pct_points"] = None
    decision = build_decision(payload)
    assert decision["decision"] == "INCONCLUSIVE"
    assert decision["criteria"]["uplift_vs_baseline_positive"] is None


def test_frozen_definition_is_preserved_in_decision_output():
    decision = build_decision(copy.deepcopy(report()))
    assert decision["frozen_experiment"] == {
        "symbol": "XRPUSDT",
        "feature": "volume_ratio_1h",
        "operator": "<=",
        "value": 0.75,
        "frozen_at_ms": FROZEN_AT_MS,
        "outcome_hours": 24,
    }
