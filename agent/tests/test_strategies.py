from app.market.types import IndicatorSnapshot, MarketCandidate, MarketRegime, TimeframeAnalysis
from app.strategies import (
    BreakoutStrategy,
    HypothesisDirection,
    MeanReversionStrategy,
    MomentumStrategy,
    PullbackStrategy,
    StrategyEngine,
    StrategyState,
    TrendFollowingStrategy,
)


def frame(
    interval,
    *,
    price=100.0,
    ema_fast=102.0,
    ema_slow=98.0,
    rsi=58.0,
    atr=2.0,
    atr_pct=2.0,
    volume_ratio=1.5,
    structure="higher_highs_higher_lows",
    regime=MarketRegime.BULLISH,
):
    return TimeframeAnalysis(
        interval=interval,
        candles=200,
        last_price=price,
        indicators=IndicatorSnapshot(
            ema_fast=ema_fast,
            ema_slow=ema_slow,
            rsi=rsi,
            atr=atr,
            atr_pct=atr_pct,
            volume_ratio=volume_ratio,
            structure=structure,
        ),
        regime=regime,
    )


def candidate(*frames):
    return MarketCandidate(
        symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
        quote_volume_24h=900_000_000,
        price_change_pct_24h=2.0,
        trade_count_24h=1_000_000,
        analyses=tuple(frames),
        ranking_score=99.0,
    )


def test_trend_strategy_watches_confirmed_multi_timeframe_trend():
    item = candidate(frame("4h"), frame("1d"))
    result = TrendFollowingStrategy().evaluate(item)
    assert result.state is StrategyState.WATCH
    assert result.direction is HypothesisDirection.BUY
    assert result.score >= 75
    assert result.risk_reward == 2.5


def test_pullback_strategy_requires_price_near_fast_ema():
    item = candidate(
        frame("1h", price=100, ema_fast=100.4, rsi=48, volume_ratio=1.0),
        frame("4h"),
        frame("1d"),
    )
    result = PullbackStrategy().evaluate(item)
    assert result.direction is HypothesisDirection.BUY
    assert result.state is StrategyState.WATCH
    assert "price is near 1h EMA20" in result.reasons


def test_breakout_waits_without_volume_confirmation():
    item = candidate(
        frame("1h", volume_ratio=1.0),
        frame("4h"),
    )
    result = BreakoutStrategy().evaluate(item)
    assert result.state is StrategyState.WAIT
    assert result.direction is HypothesisDirection.BUY


def test_mean_reversion_rejects_trending_market():
    item = candidate(
        frame("1h", rsi=30, price=95, ema_fast=100),
        frame("4h", regime=MarketRegime.BULLISH),
    )
    result = MeanReversionStrategy().evaluate(item)
    assert result.state is StrategyState.REJECT
    assert result.direction is None


def test_mean_reversion_watches_ranging_oversold_market():
    item = candidate(
        frame("1h", rsi=30, price=95, ema_fast=100, volume_ratio=1.0),
        frame("4h", regime=MarketRegime.RANGING, structure="mixed"),
    )
    result = MeanReversionStrategy().evaluate(item)
    assert result.state is StrategyState.WATCH
    assert result.direction is HypothesisDirection.BUY


def test_momentum_requires_volume():
    item = candidate(
        frame("1h", rsi=62, volume_ratio=1.0),
        frame("4h"),
    )
    result = MomentumStrategy().evaluate(item)
    assert result.state is StrategyState.WAIT


def test_engine_evaluates_all_five_strategies_without_using_ranking_score_as_confidence():
    item = candidate(
        frame("1h", price=100, ema_fast=100.5, rsi=58, volume_ratio=1.5),
        frame("4h"),
        frame("1d"),
    )
    results = StrategyEngine().evaluate(item)
    assert len(results) == 5
    assert {result.strategy for result in results} == {
        "trend_following",
        "pullback",
        "breakout",
        "mean_reversion",
        "momentum",
    }
    assert all(result.confidence != item.ranking_score for result in results)


def test_rejected_assessment_cannot_carry_direction():
    from app.strategies.base import StrategyAssessment

    try:
        StrategyAssessment(
            symbol="BTCUSDT",
            strategy="bad",
            state=StrategyState.REJECT,
            direction=HypothesisDirection.BUY,
            score=0,
            confidence=0,
            timeframe="1h",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("expected rejected assessment validation to fail")
