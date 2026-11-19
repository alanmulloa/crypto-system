from app.evaluation.campaign_operations import (
    build_campaign_progress,
    build_screening_readiness,
    evaluate_interval_health,
)
from app.evaluation.research_campaign import ResearchCampaign
from app.market.types import Candle


def campaign() -> ResearchCampaign:
    return ResearchCampaign(
        id="forward",
        strategy="mean_reversion",
        symbols=("BTCUSDT",),
        start_at="2026-11-20T00:00:00+00:00",
        end_at="2026-11-30T00:00:00+00:00",
        outcome_hours=24,
        min_bucket_observations=20,
        max_points=8000,
        fee_bps=10.0,
        slippage_bps=5.0,
        ruleset="phase5f1-predefined-buckets-v1",
    )


def test_progress_is_clamped_and_time_gated():
    item = campaign()
    before = build_campaign_progress(item, as_of_ms=item.start_ms - 1)
    middle = build_campaign_progress(
        item,
        as_of_ms=item.start_ms + (item.end_ms - item.start_ms) // 2,
    )
    after = build_campaign_progress(item, as_of_ms=item.end_ms + 1)
    assert before.progress_pct == 0.0
    assert middle.progress_pct == 50.0
    assert after.progress_pct == 100.0
    assert after.screening_allowed is True


def test_interval_health_detects_fresh_gap_free_candles():
    hour = 60 * 60 * 1000
    now = 10 * hour
    candles = (
        Candle(7 * hour, 1, 1, 1, 1, 1, 8 * hour - 1),
        Candle(8 * hour, 1, 1, 1, 1, 1, 9 * hour - 1),
        Candle(9 * hour, 1, 1, 1, 1, 1, 10 * hour - 1),
    )
    result = evaluate_interval_health("1h", candles, as_of_ms=now)
    assert result.healthy is True
    assert result.gap_count == 0
    assert result.duplicate_open_times == 0


def test_screening_cannot_start_before_fixed_window_end():
    item = campaign()
    progress = build_campaign_progress(item, as_of_ms=item.start_ms)
    readiness = build_screening_readiness(
        campaign=item,
        progress=progress,
        data_health={
            "campaign_fingerprint_sha256": item.fingerprint(),
            "all_symbols_healthy": True,
        },
    )
    assert readiness.state == "COLLECTING"
    assert readiness.screening_allowed is False
    assert readiness.auto_screening is False
    assert readiness.auto_register is False
