from app.evaluation.research_campaign import ResearchCampaign, campaign_state


def campaign():
    return ResearchCampaign(
        id="forward",
        strategy="mean_reversion",
        symbols=("BTCUSDT", "ETHUSDT"),
        start_at="2026-11-20T00:00:00+00:00",
        end_at="2027-05-19T00:00:00+00:00",
        outcome_hours=24,
        min_bucket_observations=20,
        max_points=8000,
        fee_bps=10.0,
        slippage_bps=5.0,
        ruleset="phase5f1-predefined-buckets-v1",
    )


def test_campaign_is_immutable_and_time_gated():
    item = campaign()
    assert campaign_state(item, as_of_ms=item.start_ms - 1) == "PLANNED"
    assert campaign_state(item, as_of_ms=item.start_ms) == "COLLECTING"
    assert campaign_state(item, as_of_ms=item.end_ms) == "SCREENING_READY"
    assert len(item.fingerprint()) == 64
