from app.portfolio.history import build_portfolio_history


def row(ts, total, cash=0, risk=0):
    return {
        "generated_at": ts,
        "content_hash": ts,
        "total_value_usd": total,
        "cash_value_usd": cash,
        "capital_at_risk_usd": risk,
    }


def test_history_computes_value_change_without_calling_it_return():
    payload = build_portfolio_history(
        [
            row("2026-10-20T12:00:00+00:00", 1000),
            row("2026-11-13T12:00:00+00:00", 1100),
            row("2026-11-19T12:00:00+00:00", 1200),
            row("2026-11-20T12:00:00+00:00", 1250),
        ]
    )
    assert payload["snapshot_count"] == 4
    assert payload["value_change"]["24h"]["absolute_usd"] == 50
    assert payload["value_change"]["7d"]["absolute_usd"] == 150
    assert payload["value_change"]["30d"]["absolute_usd"] == 250
    assert payload["metric_semantics"]["value_change_is_investment_return"] is False


def test_history_marks_window_unavailable_without_baseline():
    payload = build_portfolio_history(
        [row("2026-11-20T12:00:00+00:00", 1250)]
    )
    assert payload["value_change"]["24h"]["available"] is False
    assert payload["value_change"]["7d"]["available"] is False
    assert payload["value_change"]["30d"]["available"] is False
