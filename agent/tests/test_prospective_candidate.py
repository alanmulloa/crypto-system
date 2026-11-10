import pytest

from app.evaluation.historical import HistoricalPoint
from app.evaluation.prospective_candidate import (
    ProspectiveXrpCandidateEvaluator,
    parse_iso_ms,
)
from app.market.types import (
    Candle,
    IndicatorSnapshot,
    MarketCandidate,
    MarketRegime,
    TimeframeAnalysis,
)
from app.strategies import (
    AggregatedAssessment,
    HypothesisDirection,
    StrategyAssessment,
    StrategyState,
)


HOUR = 60 * 60 * 1000


def candle(index, *, close=100):
    return Candle(
        open_time_ms=index * HOUR,
        open=100,
        high=max(101, close),
        low=min(99, close),
        close=close,
        volume=1000,
        close_time_ms=(index + 1) * HOUR - 1,
    )


def point(index, *, volume_ratio=0.5):
    indicator = IndicatorSnapshot(
        ema_fast=100,
        ema_slow=101,
        rsi=30,
        atr=2,
        atr_pct=2,
        volume_ratio=volume_ratio,
        structure="mixed",
    )
    analyses = tuple(
        TimeframeAnalysis(
            interval=interval,
            candles=100,
            last_price=100,
            indicators=indicator,
            regime=MarketRegime.RANGING,
        )
        for interval in ("15m", "1h", "4h", "1d")
    )
    item = StrategyAssessment(
        symbol="XRPUSDT",
        strategy="mean_reversion",
        state=StrategyState.WATCH,
        direction=HypothesisDirection.BUY,
        score=80,
        confidence=80,
        timeframe="1h+4h",
        entry_low=95,
        entry_high=105,
        stop=90,
        tp1=110,
    )
    candidate = MarketCandidate(
        symbol="XRPUSDT",
        base_asset="XRP",
        quote_asset="USDT",
        quote_volume_24h=0,
        price_change_pct_24h=0,
        trade_count_24h=0,
        analyses=analyses,
    )
    aggregate = AggregatedAssessment(
        symbol="XRPUSDT",
        state=StrategyState.WATCH,
        direction=HypothesisDirection.BUY,
        score=80,
        confidence=80,
        supporting_strategies=("mean_reversion",),
    )
    return HistoricalPoint(
        timestamp_ms=(index + 1) * HOUR - 1,
        candidate=candidate,
        assessments=(item,),
        aggregate=aggregate,
    )


def evaluator(*, freeze=0, minimum=1):
    return ProspectiveXrpCandidateEvaluator(
        frozen_at_ms=freeze,
        min_matured_observations=minimum,
        fee_bps=0,
        slippage_bps=0,
    )


def test_iso_cutoff_is_deterministic():
    assert parse_iso_ms("1970-01-01T00:00:01+00:00") == 1000


def test_pre_freeze_signal_is_never_included():
    tool = evaluator(freeze=3 * HOUR)
    result = tool.run(
        points=(point(1), point(4)),
        candles_by_interval={"1h": tuple(candle(i) for i in range(40))},
        as_of_ms=40 * HOUR,
    )
    assert result.baseline.observations == 1


def test_candidate_is_subset_of_xrp_baseline():
    tool = evaluator()
    result = tool.run(
        points=(point(1, volume_ratio=0.5), point(2, volume_ratio=1.0)),
        candles_by_interval={"1h": tuple(candle(i) for i in range(40))},
        as_of_ms=40 * HOUR,
    )
    assert result.baseline.observations == 2
    assert result.candidate_summary.observations == 1


def test_pending_outcome_is_not_fabricated():
    tool = evaluator()
    result = tool.run(
        points=(point(1),),
        candles_by_interval={"1h": tuple(candle(i) for i in range(10))},
        as_of_ms=10 * HOUR,
    )
    assert result.candidate_summary.matured == 0
    assert result.candidate_summary.pending == 1
    assert result.candidate_summary.average_net_return_pct is None


def test_matured_outcome_uses_24h_future_close():
    candles = [candle(i, close=100) for i in range(40)]
    candles[25] = candle(25, close=102)
    tool = evaluator()
    result = tool.run(
        points=(point(1),),
        candles_by_interval={"1h": tuple(candles)},
        as_of_ms=40 * HOUR,
    )
    assert result.candidate_summary.matured == 1
    assert result.candidate_summary.average_net_return_pct == pytest.approx(2.0)


def test_sample_ready_depends_on_candidate_matured_count_only():
    tool = evaluator(minimum=2)
    result = tool.run(
        points=(point(1),),
        candles_by_interval={"1h": tuple(candle(i) for i in range(40))},
        as_of_ms=40 * HOUR,
    )
    assert result.sample_ready is False


def test_as_of_must_be_after_freeze():
    tool = evaluator(freeze=10 * HOUR)
    with pytest.raises(ValueError, match="after frozen_at_ms"):
        tool.run(points=(), candles_by_interval={"1h": (candle(0),)}, as_of_ms=9 * HOUR)
