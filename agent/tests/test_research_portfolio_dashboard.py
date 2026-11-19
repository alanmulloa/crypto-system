from app.evaluation.research_portfolio_dashboard import (
    build_research_portfolio_dashboard,
)


def test_dashboard_never_auto_registers():
    payload = build_research_portfolio_dashboard(
        campaign_statuses=(
            {
                "campaign_id": "forward",
                "state": "COLLECTING",
                "screening_allowed": False,
            },
        ),
        queues=(),
        registry_summary={"experiments": 1},
    )
    assert payload["automatic_registration"] is False
    assert payload["automatic_freeze"] is False
    assert payload["phase6_blocked"] is True
