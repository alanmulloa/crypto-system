from app.evaluation.experiment_registry import (
    ExperimentRegistry,
    ExperimentStatus,
    ResearchExperiment,
)
from app.evaluation.research_experiment_planner import plan_registry


def exp(identifier, status):
    return ResearchExperiment(
        id=identifier,
        symbol="BTCUSDT",
        strategy="mean_reversion",
        direction="BUY",
        feature="volume_ratio_1h",
        operator="<=",
        threshold=0.75,
        calibration_period=None,
        validation_period=None,
        freeze_at_ms=1000 if status in {
            ExperimentStatus.FROZEN,
            ExperimentStatus.PROSPECTIVE,
        } else None,
        outcome_hours=24,
        fee_bps=10.0,
        slippage_bps=5.0,
        status=status,
        decision=None,
        artifact_path="reports/research/",
    )


def test_planner_keeps_phase5g_on_legacy_pipeline():
    registry = ExperimentRegistry(
        (
            exp(
                "phase5g-xrp-low-volume-1h",
                ExperimentStatus.PROSPECTIVE,
            ),
        )
    )
    item = plan_registry(registry)[0]
    assert item.pipeline == "PHASE5G_LEGACY"
    assert item.next_action == "CONTINUE_EXISTING_PHASE5G"


def test_planner_requires_bootstrap_for_frozen_generic_experiment():
    registry = ExperimentRegistry((exp("future", ExperimentStatus.FROZEN),))
    item = plan_registry(registry)[0]
    assert item.next_action == "BOOTSTRAP_REQUIRED"
    assert item.automatic_transition is False
