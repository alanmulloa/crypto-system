from dataclasses import replace

import pytest

from app.evaluation.candidate_experiment import (
    DEFAULT_CANDIDATES,
    MeanReversionCandidateExperiment,
)
from app.evaluation.entry_quality import (
    EntryFeatureSnapshot,
    EntryQualitySymbolReport,
    EntrySegmentReport,
)


def snapshot(
    *,
    symbol="XRPUSDT",
    segment="calibration",
    volume=0.5,
    structure_4h="mixed",
    result=1.0,
):
    return EntryFeatureSnapshot(
        symbol=symbol,
        segment=segment,
        signal_timestamp_ms=1,
        score=80,
        confidence=80,
        rsi_1h=30,
        atr_pct_1h=1,
        volume_ratio_1h=volume,
        ema_distance_pct_1h=-1,
        ema_spread_pct_1h=-1,
        rsi_15m=40,
        ema_distance_pct_15m=-1,
        rsi_4h=45,
        ema_distance_pct_4h=-1,
        below_ema_fast_timeframes=3,
        structure_1h="mixed",
        structure_4h=structure_4h,
        hours_since_previous_watch_buy=2,
        watch_buy_signals_last_6h=2,
        outcome_hours=24,
        net_return_pct=result,
        positive_return=result > 0,
    )


def segment(name, observations):
    return EntrySegmentReport(
        segment=name,
        observations=tuple(observations),
        baseline_return_pct=None,
        buckets=(),
        research_eligible=name != "out_of_sample",
    )


def report(symbol, cal, val, oos):
    return EntryQualitySymbolReport(
        symbol=symbol,
        strategy="mean_reversion",
        outcome_hours=24,
        segments=(
            segment("calibration", cal),
            segment("validation", val),
            segment("out_of_sample", oos),
        ),
        cross_segment_evidence=(),
    )


def test_xrp_candidate_compares_against_segment_baseline():
    candidate = DEFAULT_CANDIDATES[0]
    cal = (
        snapshot(volume=0.5, result=2),
        snapshot(volume=1.2, result=-2),
    )
    val = (
        snapshot(segment="validation", volume=0.4, result=3),
        snapshot(segment="validation", volume=1.3, result=-1),
    )
    oos = (snapshot(segment="out_of_sample", volume=0.4, result=-10),)
    result = MeanReversionCandidateExperiment(min_observations=1).run(
        report=report("XRPUSDT", cal, val, oos),
        candidate=candidate,
    )

    calibration = result.segments[0]
    assert calibration.baseline_average_return_pct == pytest.approx(0)
    assert calibration.candidate_average_return_pct == pytest.approx(2)
    assert calibration.uplift_vs_baseline_pct_points == pytest.approx(2)
    assert result.stable_positive_return is True
    assert result.stable_positive_uplift is True
    assert result.eligible_for_future_prospective_test is True


def test_oos_never_changes_candidate_selection():
    candidate = DEFAULT_CANDIDATES[0]
    cal = (snapshot(result=2),)
    val = (snapshot(segment="validation", result=3),)
    bad_oos = (snapshot(segment="out_of_sample", result=-50),)
    good_oos = (replace(bad_oos[0], net_return_pct=50, positive_return=True),)

    tool = MeanReversionCandidateExperiment(min_observations=1)
    first = tool.run(
        report=report("XRPUSDT", cal, val, bad_oos),
        candidate=candidate,
    )
    second = tool.run(
        report=report("XRPUSDT", cal, val, good_oos),
        candidate=candidate,
    )

    assert first.eligible_for_future_prospective_test is True
    assert second.eligible_for_future_prospective_test is True
    assert first.segments[2].research_eligible is False


def test_candidate_requires_sufficient_sample_in_both_eligible_segments():
    candidate = DEFAULT_CANDIDATES[0]
    cal = tuple(snapshot(result=1) for _ in range(2))
    val = (snapshot(segment="validation", result=1),)
    oos = ()
    result = MeanReversionCandidateExperiment(min_observations=2).run(
        report=report("XRPUSDT", cal, val, oos),
        candidate=candidate,
    )
    assert result.sufficient_sample_both is False
    assert result.eligible_for_future_prospective_test is False


def test_eth_candidate_uses_market_structure_not_volume():
    candidate = DEFAULT_CANDIDATES[1]
    cal = (
        snapshot(
            symbol="ETHUSDT",
            structure_4h="lower_highs_lower_lows",
            volume=5,
            result=1,
        ),
        snapshot(symbol="ETHUSDT", structure_4h="mixed", volume=0.1, result=-1),
    )
    val = (
        snapshot(
            symbol="ETHUSDT",
            segment="validation",
            structure_4h="lower_highs_lower_lows",
            volume=5,
            result=1,
        ),
    )
    result = MeanReversionCandidateExperiment(min_observations=1).run(
        report=report("ETHUSDT", cal, val, ()),
        candidate=candidate,
    )
    assert result.segments[0].candidate_observations == 1


def test_symbol_mismatch_is_rejected():
    with pytest.raises(ValueError, match="requires XRPUSDT"):
        MeanReversionCandidateExperiment(min_observations=1).run(
            report=report("BTCUSDT", (), (), ()),
            candidate=DEFAULT_CANDIDATES[0],
        )
