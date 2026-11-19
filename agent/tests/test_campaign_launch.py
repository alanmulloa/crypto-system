from app.evaluation.campaign_launch import build_campaign_launch_status
from app.evaluation.research_campaign import ResearchCampaign


def campaign():
    return ResearchCampaign(
        id="core-mean-reversion-forward-2026-11",
        strategy="mean_reversion",
        symbols=(
            "BTCUSDT",
            "ETHUSDT",
            "BNBUSDT",
            "SOLUSDT",
            "XRPUSDT",
        ),
        start_at="2026-11-20T00:00:00+00:00",
        end_at="2027-05-19T00:00:00+00:00",
        outcome_hours=24,
        min_bucket_observations=20,
        max_points=8000,
        fee_bps=10.0,
        slippage_bps=5.0,
        ruleset="phase5f1-predefined-buckets-v1",
    )


def seal(item):
    return {
        "sealed_definition": item.to_dict(),
        "research_only": True,
        "phase6_blocked": True,
    }


def ops(healthy=True, screening=False):
    return {
        "data_health": {
            "all_symbols_healthy": healthy,
            "as_of_ms": 0,
        },
        "screening_readiness": {
            "screening_allowed": screening,
        },
    }


def test_prestart_ready_when_definition_and_data_are_valid():
    item = campaign()
    result = build_campaign_launch_status(
        campaign=item,
        launch_seal=seal(item),
        operations=ops(True),
        as_of_ms=item.start_ms - 1,
    )
    assert result["state"] == "PRESTART_READY"
    assert result["definition_matches_seal"] is True
    assert result["phase6_blocked"] is True


def test_first_day_smoke_state_is_explicit():
    item = campaign()
    result = build_campaign_launch_status(
        campaign=item,
        launch_seal=seal(item),
        operations=ops(True),
        as_of_ms=item.start_ms + 60_000,
    )
    assert result["state"] == "FIRST_DAY_HEALTHY"
    assert result["first_day_window"] is True
    assert result["automatic_screening"] is False


def test_definition_drift_blocks_launch():
    item = campaign()
    changed = item.to_dict()
    changed["fee_bps"] = 11.0
    result = build_campaign_launch_status(
        campaign=item,
        launch_seal={"sealed_definition": changed},
        operations=ops(True),
        as_of_ms=item.start_ms,
    )
    assert result["state"] == "BLOCKED_DEFINITION_DRIFT"
    assert result["definition_matches_seal"] is False
    assert result["phase6_eligible"] is False


def test_screening_stays_disabled_during_campaign():
    item = campaign()
    result = build_campaign_launch_status(
        campaign=item,
        launch_seal=seal(item),
        operations=ops(True, screening=False),
        as_of_ms=item.start_ms + 10_000_000,
    )
    assert result["screening_allowed"] is False
    assert result["automatic_screening"] is False
