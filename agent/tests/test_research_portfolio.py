from app.evaluation.experiment_registry import ExperimentRegistry
from app.evaluation.research_portfolio import build_promotion_queue


def proposal(identifier, symbol, feature, uplift=0.5):
    return {
        "id": identifier,
        "symbol": symbol,
        "strategy": "mean_reversion",
        "direction": "BUY",
        "feature": feature,
        "operator": "<=",
        "threshold": 0.75,
        "outcome_hours": 24,
        "validation_uplift_pct_points": uplift,
    }


def test_queue_limits_concurrency_and_symbol_diversity():
    queue = build_promotion_queue(
        proposals=(
            proposal("a", "BTCUSDT", "volume_ratio_1h"),
            proposal("b", "BTCUSDT", "rsi_1h"),
            proposal("c", "ETHUSDT", "structure_4h"),
        ),
        registry=ExperimentRegistry(()),
        max_new_concurrent=2,
    )
    assert queue[0].decision == "READY_FOR_HUMAN_REGISTRATION"
    assert queue[1].decision == "DEFER_SYMBOL_DIVERSITY"
    assert queue[2].decision == "READY_FOR_HUMAN_REGISTRATION"
    assert queue[0].auto_register is False
