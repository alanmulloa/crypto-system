import json

import pytest

from app.evaluation.experiment_registry import (
    ExperimentRegistry,
    ExperimentStatus,
    ResearchExperiment,
)
from app.evaluation.proposal_review import (
    MIN_VALIDATION_UPLIFT_PCT_POINTS,
    review_discovery_payload,
    review_proposal,
)
from app.evaluation.proposal_review_cli import main as review_cli_main


def experiment(**changes):
    values = {
        "id": "tracked",
        "symbol": "XRPUSDT",
        "strategy": "mean_reversion",
        "direction": "BUY",
        "feature": "volume_ratio_1h",
        "operator": "<=",
        "threshold": 0.75,
        "calibration_period": None,
        "validation_period": None,
        "freeze_at_ms": 100,
        "outcome_hours": 24,
        "fee_bps": 10.0,
        "slippage_bps": 5.0,
        "status": ExperimentStatus.PROSPECTIVE,
        "decision": "NOT_READY",
        "artifact_path": "reports/phase5g/",
    }
    values.update(changes)
    return ResearchExperiment(**values)


def proposal(**changes):
    values = {
        "id": "xrpusdt-volume_ratio_1h-lte-0p75",
        "symbol": "XRPUSDT",
        "strategy": "mean_reversion",
        "direction": "BUY",
        "feature": "volume_ratio_1h",
        "operator": "<=",
        "threshold": 0.75,
        "outcome_hours": 24,
        "validation_uplift_pct_points": 0.586,
    }
    values.update(changes)
    return values


def discovery_payload(*items):
    return {
        "metadata": {
            "phase": "5H.4",
            "research_only": True,
            "auto_register": False,
            "auto_freeze": False,
        },
        "proposals": list(items),
    }


def test_exact_rule_is_already_tracked():
    registry = ExperimentRegistry((experiment(),))
    result = review_proposal(proposal(), registry)
    assert result.decision == "ALREADY_TRACKED"
    assert result.matched_experiment_id == "tracked"


def test_overlapping_rule_requires_human_review():
    registry = ExperimentRegistry((experiment(threshold=0.6),))
    result = review_proposal(proposal(), registry)
    assert result.decision == "HUMAN_REVIEW"
    assert result.matched_experiment_id == "tracked"


def test_weak_validation_is_rejected():
    registry = ExperimentRegistry(tuple())
    result = review_proposal(
        proposal(
            symbol="ETHUSDT",
            feature="structure_4h",
            operator="==",
            threshold="lower_highs_lower_lows",
            validation_uplift_pct_points=0.011,
        ),
        registry,
    )
    assert result.decision == "REJECT_WEAK_VALIDATION"


def test_threshold_boundary_is_ready_to_register():
    registry = ExperimentRegistry(tuple())
    result = review_proposal(
        proposal(
            symbol="BTCUSDT",
            validation_uplift_pct_points=MIN_VALIDATION_UPLIFT_PCT_POINTS,
        ),
        registry,
    )
    assert result.decision == "READY_TO_REGISTER"


def test_strong_new_proposal_is_ready_to_register():
    registry = ExperimentRegistry(tuple())
    result = review_proposal(
        proposal(symbol="BTCUSDT", validation_uplift_pct_points=0.25),
        registry,
    )
    assert result.decision == "READY_TO_REGISTER"
    assert result.auto_register is False
    assert result.auto_freeze is False
    assert result.phase6_blocked is True


def test_invalid_phase5h4_artifact_is_rejected():
    registry = ExperimentRegistry(tuple())
    with pytest.raises(ValueError, match="Phase 5H.4"):
        review_discovery_payload(
            {"metadata": {"phase": "5F.1"}, "proposals": []},
            registry,
        )


def test_auto_register_must_be_false():
    registry = ExperimentRegistry(tuple())
    bad = discovery_payload()
    bad["metadata"]["auto_register"] = True
    with pytest.raises(ValueError, match="auto_register=false"):
        review_discovery_payload(bad, registry)


def test_cli_classifies_xrp_and_eth(tmp_path, capsys):
    registry_path = tmp_path / "registry.json"
    source = tmp_path / "discovery.json"
    output = tmp_path / "review.json"

    ExperimentRegistry((experiment(),)).save(registry_path)
    source.write_text(
        json.dumps(
            discovery_payload(
                proposal(),
                proposal(
                    id="ethusdt-structure_4h-eq-lower_highs_lower_lows",
                    symbol="ETHUSDT",
                    feature="structure_4h",
                    operator="==",
                    threshold="lower_highs_lower_lows",
                    validation_uplift_pct_points=0.011,
                ),
            )
        ),
        encoding="utf-8",
    )

    assert review_cli_main(
        [
            "--input",
            str(source),
            "--registry",
            str(registry_path),
            "--output",
            str(output),
        ]
    ) == 0

    stdout = capsys.readouterr().out
    assert "xrpusdt-volume_ratio_1h-lte-0p75 | ALREADY_TRACKED" in stdout
    assert (
        "ethusdt-structure_4h-eq-lower_highs_lower_lows "
        "| REJECT_WEAK_VALIDATION"
    ) in stdout

    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["metadata"]["auto_register"] is False
    assert result["metadata"]["phase6_blocked"] is True
    assert result["decision_counts"] == {
        "ALREADY_TRACKED": 1,
        "REJECT_WEAK_VALIDATION": 1,
    }
