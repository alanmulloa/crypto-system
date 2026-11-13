import json

import pytest

from app.evaluation.experiment_registry import (
    ExperimentRegistry,
    ExperimentStatus,
    ResearchExperiment,
)
from app.evaluation.validation_harness import (
    MIN_VALIDATION_OBSERVATIONS,
    MIN_VALIDATION_UPLIFT_PCT_POINTS,
    run_validation_review,
)
from app.evaluation.validation_harness_cli import main as validation_cli_main


def experiment(**changes):
    values = {
        "id": "btc-low-volume",
        "symbol": "BTCUSDT",
        "strategy": "mean_reversion",
        "direction": "BUY",
        "feature": "volume_ratio_1h",
        "operator": "<=",
        "threshold": 0.75,
        "calibration_period": None,
        "validation_period": None,
        "freeze_at_ms": None,
        "outcome_hours": 24,
        "fee_bps": 10.0,
        "slippage_bps": 5.0,
        "status": ExperimentStatus.VALIDATION,
        "decision": None,
        "artifact_path": "reports/research/btc-low-volume/",
    }
    values.update(changes)
    return ResearchExperiment(**values)


def bucket_row(**changes):
    values = {
        "segment": "validation",
        "feature": "volume_ratio_1h",
        "bucket": "<=0.75",
        "observations": 25,
        "average_return_pct": 0.4,
        "median_return_pct": 0.2,
        "positive_return_rate_pct": 60.0,
        "baseline_return_pct": -0.1,
        "uplift_vs_baseline_pct_points": 0.25,
        "sufficient_sample": True,
        "research_eligible": True,
    }
    values.update(changes)
    return values


def payload(*rows):
    return {
        "metadata": {
            "phase": "5F.1",
            "research_only": True,
        },
        "results": [
            {
                "symbol": "BTCUSDT",
                "strategy": "mean_reversion",
                "outcome_hours": 24,
                "segments": [
                    {
                        "segment": "calibration",
                        "observations": [],
                        "baseline_return_pct": 999.0,
                        "buckets": [
                            bucket_row(
                                segment="calibration",
                                average_return_pct=-999.0,
                                uplift_vs_baseline_pct_points=-999.0,
                            )
                        ],
                        "research_eligible": True,
                    },
                    {
                        "segment": "validation",
                        "observations": [],
                        "baseline_return_pct": -0.1,
                        "buckets": list(rows),
                        "research_eligible": True,
                    },
                    {
                        "segment": "out_of_sample",
                        "observations": [],
                        "baseline_return_pct": 999.0,
                        "buckets": [
                            bucket_row(
                                segment="out_of_sample",
                                average_return_pct=-999.0,
                                uplift_vs_baseline_pct_points=-999.0,
                            )
                        ],
                        "research_eligible": False,
                    },
                ],
                "cross_segment_evidence": [],
            }
        ],
    }


def test_validation_passes_all_preregistered_criteria():
    review = run_validation_review(
        experiment=experiment(),
        phase5f1_payload=payload(bucket_row()),
    )
    assert review.decision == "PASS_VALIDATION"
    assert review.eligible_for_freeze_review is True
    assert review.auto_transition is False


def test_calibration_and_oos_cannot_change_validation_decision():
    review = run_validation_review(
        experiment=experiment(),
        phase5f1_payload=payload(bucket_row()),
    )
    assert review.decision == "PASS_VALIDATION"
    assert review.average_return_pct == 0.4


@pytest.mark.parametrize(
    "changes",
    [
        {"observations": MIN_VALIDATION_OBSERVATIONS - 1},
        {"average_return_pct": 0.0},
        {"median_return_pct": 0.0},
        {"positive_return_rate_pct": 50.0},
        {
            "uplift_vs_baseline_pct_points": (
                MIN_VALIDATION_UPLIFT_PCT_POINTS - 0.001
            )
        },
    ],
)
def test_each_failed_criterion_fails_validation(changes):
    review = run_validation_review(
        experiment=experiment(),
        phase5f1_payload=payload(bucket_row(**changes)),
    )
    assert review.decision == "FAIL_VALIDATION"
    assert review.eligible_for_freeze_review is False


def test_uplift_threshold_boundary_passes():
    review = run_validation_review(
        experiment=experiment(),
        phase5f1_payload=payload(
            bucket_row(
                uplift_vs_baseline_pct_points=(
                    MIN_VALIDATION_UPLIFT_PCT_POINTS
                )
            )
        ),
    )
    assert review.decision == "PASS_VALIDATION"


def test_missing_bucket_is_inconclusive():
    review = run_validation_review(
        experiment=experiment(),
        phase5f1_payload=payload(),
    )
    assert review.decision == "INCONCLUSIVE"
    assert review.eligible_for_freeze_review is False


def test_requires_validation_status():
    with pytest.raises(ValueError, match="status VALIDATION"):
        run_validation_review(
            experiment=experiment(status=ExperimentStatus.CALIBRATION),
            phase5f1_payload=payload(bucket_row()),
        )


def test_requires_phase5f1_artifact():
    bad = payload(bucket_row())
    bad["metadata"]["phase"] = "5H.4"
    with pytest.raises(ValueError, match="Phase 5F.1"):
        run_validation_review(
            experiment=experiment(),
            phase5f1_payload=bad,
        )


def test_cli_writes_research_only_artifact(tmp_path, capsys):
    source = tmp_path / "phase5f1.json"
    registry_path = tmp_path / "registry.json"
    output = tmp_path / "validation.json"

    source.write_text(json.dumps(payload(bucket_row())), encoding="utf-8")
    ExperimentRegistry((experiment(),)).save(registry_path)

    assert validation_cli_main(
        [
            "--input",
            str(source),
            "--registry",
            str(registry_path),
            "--experiment-id",
            "btc-low-volume",
            "--output",
            str(output),
        ]
    ) == 0

    stdout = capsys.readouterr().out
    assert "btc-low-volume | PASS_VALIDATION | observations=25" in stdout

    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["metadata"]["segment_used"] == "validation"
    assert result["metadata"]["calibration_read"] is False
    assert result["metadata"]["oos_read"] is False
    assert result["metadata"]["auto_transition"] is False
    assert result["metadata"]["phase6_blocked"] is True
