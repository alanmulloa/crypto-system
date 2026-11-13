import json

import pytest

from app.evaluation.experiment_registry import ExperimentStatus, ResearchExperiment
from app.evaluation.freeze_manifest import canonical_json_sha256, freeze_definition
from app.evaluation.prospective_bootstrap import (
    assert_generic_history_compatible,
    build_generic_protocol,
    validate_generic_report,
)


def experiment(**changes):
    values = {
        "id": "future-candidate",
        "symbol": "BTCUSDT",
        "strategy": "mean_reversion",
        "direction": "BUY",
        "feature": "volume_ratio_1h",
        "operator": "<=",
        "threshold": 0.75,
        "calibration_period": "cal",
        "validation_period": "val",
        "freeze_at_ms": 1_000_000,
        "outcome_hours": 24,
        "fee_bps": 10.0,
        "slippage_bps": 5.0,
        "status": ExperimentStatus.FROZEN,
        "decision": "READY_FOR_FREEZE",
        "artifact_path": "reports/research/future-candidate/",
    }
    values.update(changes)
    return ResearchExperiment(**values)


def manifest(exp):
    definition = freeze_definition(exp)
    return {
        "metadata": {
            "phase": "5H.9",
            "research_only": True,
            "phase6_blocked": True,
        },
        "experiment_id": exp.id,
        "frozen_definition": definition,
        "definition_fingerprint_sha256": canonical_json_sha256(definition),
    }


def protocol(exp=None):
    selected = exp or experiment()
    return build_generic_protocol(
        experiment=selected,
        freeze_manifest=manifest(selected),
    )


def report(p, *, status="PENDING", signal_ms=None):
    signal = signal_ms if signal_ms is not None else p.frozen_at_ms + 1
    item = {
        "cohort": "candidate",
        "symbol": p.symbol,
        "signal_timestamp_ms": signal,
        "entry_timestamp_ms": signal + 1,
        "entry_market_price": 100.0,
        "feature_value": 0.5,
        "status": status,
        "outcome_timestamp_ms": None,
        "gross_return_pct": None,
        "net_return_pct": None,
        "positive_return": None,
    }
    if status == "MATURED":
        item["outcome_timestamp_ms"] = (
            item["entry_timestamp_ms"] + p.outcome_hours * 60 * 60 * 1000 - 1
        )
        item["gross_return_pct"] = 1.0
        item["net_return_pct"] = 0.8
        item["positive_return"] = True

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
        "baseline": {},
        "candidate_summary": {},
        "uplift_vs_baseline_pct_points": None,
        "observations": [item],
    }


def test_bootstrap_requires_frozen_experiment():
    with pytest.raises(ValueError, match="FROZEN"):
        build_generic_protocol(
            experiment=experiment(status=ExperimentStatus.VALIDATION),
            freeze_manifest=manifest(experiment()),
        )


def test_bootstrap_uses_registry_outcome_costs_and_cutoff():
    p = protocol()
    assert p.outcome_hours == 24
    assert p.fee_bps == 10.0
    assert p.slippage_bps == 5.0
    assert p.frozen_at_ms == 1_000_000
    assert p.execution_enabled is False
    assert p.testnet_enabled is False


def test_bootstrap_rejects_manifest_definition_drift():
    exp = experiment()
    bad = manifest(exp)
    bad["frozen_definition"]["threshold"] = 0.70
    with pytest.raises(ValueError, match="drift"):
        build_generic_protocol(experiment=exp, freeze_manifest=bad)


def test_report_rejects_pre_freeze_observation():
    p = protocol()
    with pytest.raises(ValueError, match="post-freeze"):
        validate_generic_report(
            report(p, signal_ms=p.frozen_at_ms),
            protocol=p,
        )


def test_matured_requires_full_registry_outcome_horizon():
    p = protocol()
    payload = report(p, status="MATURED")
    payload["observations"][0]["outcome_timestamp_ms"] -= 1
    with pytest.raises(ValueError, match="incomplete outcome horizon"):
        validate_generic_report(payload, protocol=p)


def test_pending_may_mature_without_mutating_signal_definition():
    p = protocol()
    previous = report(p, status="PENDING")
    current = report(p, status="MATURED")
    assert_generic_history_compatible(previous, current, protocol=p)


def test_matured_outcome_is_immutable():
    p = protocol()
    previous = report(p, status="MATURED")
    current = json.loads(json.dumps(previous))
    current["observations"][0]["net_return_pct"] = 99.0
    with pytest.raises(ValueError, match="matured observation mutated"):
        assert_generic_history_compatible(previous, current, protocol=p)
