from app.evaluation.signal_scarcity import evaluate_signal_scarcity


def test_no_candidate_signal_is_descriptive_only():
    report = {
        "baseline": {"observations": 2},
        "candidate_summary": {"observations": 0, "matured": 0},
    }
    result = evaluate_signal_scarcity(
        report,
        frozen_at_ms=1000,
        as_of_ms=1000 + 7 * 24 * 60 * 60 * 1000,
    )
    assert result.state == "NO_CANDIDATE_SIGNAL"
    assert result.descriptive_only is True
