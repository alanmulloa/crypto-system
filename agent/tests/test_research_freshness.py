from datetime import datetime, timedelta, timezone

from app.evaluation.research_freshness import evaluate_freshness


def test_freshness_detects_fresh_and_stale():
    now = datetime(2026, 11, 19, 12, tzinfo=timezone.utc)
    fresh = {
        "metadata": {
            "created_at": (now - timedelta(hours=6)).isoformat(),
        }
    }
    stale = {
        "metadata": {
            "created_at": (now - timedelta(hours=13)).isoformat(),
        }
    }
    assert evaluate_freshness(fresh, as_of=now).state == "FRESH"
    assert evaluate_freshness(stale, as_of=now).state == "STALE"
