from datetime import datetime, timezone

from app.evaluation.research_health import build_research_health


def test_healthy_waiting_for_signal_does_not_change_strategy():
    now = datetime(2026, 11, 19, 12, tzinfo=timezone.utc)
    latest = {
        "metadata": {"created_at": now.isoformat()},
        "baseline": {"observations": 2},
        "candidate_summary": {"observations": 0, "matured": 0},
    }
    health = build_research_health(
        latest=latest,
        decision={"decision": "NOT_READY"},
        frozen_at_ms=1000,
        as_of_ms=int(now.timestamp() * 1000),
        as_of=now,
    )
    assert health.state == "HEALTHY_WAITING_FOR_SIGNAL"
    assert health.recommended_action == "CONTINUE_COLLECTION"
    assert health.automatic_strategy_change is False
    assert health.phase6_blocked is True
