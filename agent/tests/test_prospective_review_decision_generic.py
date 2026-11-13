import pytest

from app.evaluation.prospective_bootstrap import GenericProspectiveProtocol
from app.evaluation.prospective_decision_generic import build_generic_decision
from app.evaluation.prospective_review_generic import build_generic_review


def protocol(minimum=20):
    return GenericProspectiveProtocol(
        experiment_id="candidate",
        symbol="BTCUSDT",
        strategy="mean_reversion",
        direction="BUY",
        feature="volume_ratio_1h",
        operator="<=",
        threshold=0.75,
        frozen_at_ms=1000,
        outcome_hours=24,
        fee_bps=10.0,
        slippage_bps=5.0,
        min_matured_observations=minimum,
        definition_fingerprint_sha256="a" * 64,
    )


def report(
    p,
    *,
    observations=0,
    matured=0,
    pending=0,
    avg=None,
    median=None,
    positive_rate=None,
    baseline_avg=None,
    uplift=None,
):
    items = []
    for index in range(observations):
        items.append(
            {
                "cohort": "candidate",
                "symbol": p.symbol,
                "signal_timestamp_ms": p.frozen_at_ms + 1 + index,
                "entry_timestamp_ms": None,
                "entry_market_price": None,
                "feature_value": 0.5,
                "status": "NO_ENTRY",
                "outcome_timestamp_ms": None,
                "gross_return_pct": None,
                "net_return_pct": None,
                "positive_return": None,
            }
        )
    return {
        "metadata": {
            "phase": "5H.10-prospective",
            "created_at": "2026-11-13T00:00:00+00:00",
            "research_only": True,
            "phase6_blocked": True,
            "execution_enabled": False,
            "testnet_enabled": False,
            "automatic_promotion": False,
        },
        "frozen_experiment": {
            "experiment_id": p.experiment_id,
            "symbol": p.symbol,
            "strategy": p.strategy,
            "direction": p.direction,
            "feature": p.feature,
            "operator": p.operator,
            "threshold": p.threshold,
            "frozen_at_ms": p.frozen_at_ms,
            "outcome_hours": p.outcome_hours,
            "fee_bps": p.fee_bps,
            "slippage_bps": p.slippage_bps,
            "min_matured_observations": p.min_matured_observations,
            "definition_fingerprint_sha256": p.definition_fingerprint_sha256,
        },
        "baseline": {
            "observations": observations,
            "pending": 0,
            "matured": matured,
            "average_net_return_pct": baseline_avg,
            "median_net_return_pct": None,
            "positive_return_rate_pct": None,
        },
        "candidate_summary": {
            "observations": observations,
            "pending": pending,
            "matured": matured,
            "average_net_return_pct": avg,
            "median_net_return_pct": median,
            "positive_return_rate_pct": positive_rate,
        },
        "uplift_vs_baseline_pct_points": uplift,
        "observations": items,
    }


@pytest.mark.parametrize(
    "kwargs,state",
    [
        ({}, "WAITING_FOR_CANDIDATE_SIGNAL"),
        (
            {"observations": 2, "pending": 2},
            "WAITING_FOR_MATURITY",
        ),
        (
            {"observations": 5, "matured": 3},
            "ACCUMULATING_MATURED_SAMPLE",
        ),
        (
            {"observations": 20, "matured": 20},
            "REVIEW_REQUIRED",
        ),
    ],
)
def test_monitoring_states(kwargs, state):
    p = protocol()
    review = build_generic_review(report(p, **kwargs), protocol=p)
    assert review["state"] == state
    assert review["phase6_blocked"] is True
    assert review["phase6_eligible"] is False


def test_not_ready_before_minimum():
    p = protocol()
    decision = build_generic_decision(
        report(
            p,
            observations=19,
            matured=19,
            avg=1.0,
            median=1.0,
            positive_rate=60.0,
            baseline_avg=0.0,
            uplift=1.0,
        ),
        protocol=p,
    )
    assert decision["decision"] == "NOT_READY"


def test_inconclusive_when_metric_missing_at_minimum():
    p = protocol()
    decision = build_generic_decision(
        report(
            p,
            observations=20,
            matured=20,
            avg=1.0,
            median=None,
            positive_rate=60.0,
            baseline_avg=0.0,
            uplift=1.0,
        ),
        protocol=p,
    )
    assert decision["decision"] == "INCONCLUSIVE"


def test_pass_research_never_unblocks_phase6():
    p = protocol()
    decision = build_generic_decision(
        report(
            p,
            observations=20,
            matured=20,
            avg=1.0,
            median=0.5,
            positive_rate=60.0,
            baseline_avg=0.2,
            uplift=0.8,
        ),
        protocol=p,
    )
    assert decision["decision"] == "PASS_RESEARCH"
    assert decision["research_gate_passed"] is True
    assert decision["phase6_eligible"] is False
    assert decision["phase6_blocked"] is True
    assert decision["automatic_phase6_promotion"] is False


def test_fail_research_when_any_metric_fails():
    p = protocol()
    decision = build_generic_decision(
        report(
            p,
            observations=20,
            matured=20,
            avg=1.0,
            median=0.5,
            positive_rate=50.0,
            baseline_avg=0.2,
            uplift=0.8,
        ),
        protocol=p,
    )
    assert decision["decision"] == "FAIL_RESEARCH"


def test_integrity_failure_rejects_report_before_decision():
    p = protocol()
    payload = report(p)
    payload["frozen_experiment"]["threshold"] = 0.70
    with pytest.raises(ValueError, match="frozen experiment changed"):
        build_generic_decision(payload, protocol=p)
