from datetime import datetime, timezone

import pytest

from app.config import Settings
from app.execution import InMemoryPaperExecutionRepository, PaperBroker, PaperExecutionOrchestrator
from app.execution.paper import PaperOrderRequest, PaperOrderType, PaperSide
from app.execution.paper_loop import PaperTradingLoop, StaticPortfolioSource
from app.market.types import IndicatorSnapshot, MarketCandidate, MarketRegime, TimeframeAnalysis
from app.portfolio import AllocationTarget, CapitalState, PortfolioPosition, PortfolioSnapshot


NOW = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)


class StaticCandidates:
    def __init__(self, candidates):
        self.candidates = candidates
        self.calls = 0

    def run_scan(self):
        self.calls += 1
        return list(self.candidates)


def frame(interval, *, price=100, regime=MarketRegime.BULLISH, volume=1.5):
    return TimeframeAnalysis(
        interval=interval,
        candles=200,
        last_price=price,
        indicators=IndicatorSnapshot(
            ema_fast=102,
            ema_slow=98,
            rsi=58,
            atr=2,
            atr_pct=2,
            volume_ratio=volume,
            structure="higher_highs_higher_lows",
        ),
        regime=regime,
    )


def bullish_candidate(symbol="BTCUSDT", price=100):
    return MarketCandidate(
        symbol=symbol,
        base_asset=symbol.replace("USDT", ""),
        quote_asset="USDT",
        quote_volume_24h=1_000_000_000,
        price_change_pct_24h=2,
        trade_count_24h=1_000_000,
        analyses=(
            frame("15m", price=price),
            frame("1h", price=price),
            frame("4h", price=price),
            frame("1d", price=price),
        ),
    )


def ranging_candidate(symbol="BTCUSDT", price=100):
    return MarketCandidate(
        symbol=symbol,
        base_asset=symbol.replace("USDT", ""),
        quote_asset="USDT",
        quote_volume_24h=1_000_000_000,
        price_change_pct_24h=0,
        trade_count_24h=1_000_000,
        analyses=tuple(
            frame(interval, price=price, regime=MarketRegime.RANGING, volume=1.0)
            for interval in ("15m", "1h", "4h", "1d")
        ),
    )


def base_portfolio(*, max_btc_pct=50):
    return PortfolioSnapshot(
        positions=(
            PortfolioPosition(
                "USDC",
                1000,
                1000,
                capital_state=CapitalState.CASH_RESERVE,
            ),
        ),
        allocations=(AllocationTarget("BTC", 10, max_btc_pct),),
    )


def make_loop(
    *,
    candidate,
    settings,
    broker=None,
    repository=None,
    max_btc_pct=50,
):
    source = StaticCandidates([candidate])
    broker = broker or PaperBroker(initial_cash_usd=1000, fee_bps=0, slippage_bps=0)
    repository = repository or InMemoryPaperExecutionRepository()
    orchestrator = PaperExecutionOrchestrator(broker, repository)
    loop = PaperTradingLoop(
        candidate_source=source,
        portfolio_source=StaticPortfolioSource(base_portfolio(max_btc_pct=max_btc_pct)),
        broker=broker,
        orchestrator=orchestrator,
        settings=settings,
    )
    return loop, source, broker, repository


def enabled_settings(**overrides):
    values = dict(
        paper_loop_enabled=True,
        kill_switch=False,
        paper_default_order_usd=100,
        max_position_usd=250,
        max_daily_buy_usd=1000,
        min_cash_reserve_pct=10,
        max_open_positions=5,
        daily_loss_limit_usd=100,
    )
    values.update(overrides)
    return Settings(**values)


def test_loop_is_disabled_by_default_and_does_not_scan():
    loop, source, broker, _ = make_loop(
        candidate=bullish_candidate(),
        settings=Settings(),
    )
    result = loop.run_cycle(cycle_id="c1", now=NOW)
    assert result.enabled is False
    assert source.calls == 0
    assert broker.account.cash_usd == 1000


def test_kill_switch_stops_new_paper_order():
    loop, _, broker, repository = make_loop(
        candidate=bullish_candidate(),
        settings=enabled_settings(kill_switch=True),
    )
    result = loop.run_cycle(cycle_id="c1", now=NOW)
    assert result.items
    assert result.filled_orders == ()
    assert repository.orders == {}
    assert broker.account.cash_usd == 1000


def test_wait_or_reject_state_does_not_create_order():
    loop, _, broker, repository = make_loop(
        candidate=ranging_candidate(),
        settings=enabled_settings(),
    )
    result = loop.run_cycle(cycle_id="c1", now=NOW)
    assert result.items
    assert result.filled_orders == ()
    assert repository.orders == {}
    assert broker.account.cash_usd == 1000


def test_approved_watch_creates_capped_paper_buy():
    loop, _, broker, _ = make_loop(
        candidate=bullish_candidate(),
        settings=enabled_settings(paper_default_order_usd=200, max_position_usd=75),
    )
    result = loop.run_cycle(cycle_id="c1", now=NOW)
    assert len(result.filled_orders) == 1
    assert result.filled_orders[0].fill is not None
    assert result.filled_orders[0].fill.gross_usd == pytest.approx(75)
    assert broker.account.cash_usd == pytest.approx(925)


def test_same_cycle_is_idempotent_and_cannot_double_fill():
    repository = InMemoryPaperExecutionRepository()
    broker = PaperBroker(initial_cash_usd=1000, fee_bps=0, slippage_bps=0)
    loop, _, _, _ = make_loop(
        candidate=bullish_candidate(),
        settings=enabled_settings(),
        broker=broker,
        repository=repository,
    )
    first = loop.run_cycle(cycle_id="same", now=NOW)
    cash = broker.account.cash_usd
    second = loop.run_cycle(cycle_id="same", now=NOW)
    assert len(first.filled_orders) == 1
    assert len(second.filled_orders) == 1
    assert broker.account.cash_usd == cash
    assert len(repository.orders) == 1


def test_daily_loss_from_paper_fills_stops_next_buy():
    broker = PaperBroker(initial_cash_usd=1000, fee_bps=0, slippage_bps=0)
    broker.submit(
        PaperOrderRequest(
            idempotency_key="seed-buy",
            symbol="ETHUSDT",
            side=PaperSide.BUY,
            order_type=PaperOrderType.MARKET,
            quantity=1,
        ),
        market_price=200,
        now=NOW,
    )
    broker.submit(
        PaperOrderRequest(
            idempotency_key="seed-sell",
            symbol="ETHUSDT",
            side=PaperSide.SELL,
            order_type=PaperOrderType.MARKET,
            quantity=1,
        ),
        market_price=50,
        now=NOW,
    )
    assert broker.daily_realized_pnl(NOW) == pytest.approx(-150)

    loop, _, _, repository = make_loop(
        candidate=bullish_candidate(),
        settings=enabled_settings(daily_loss_limit_usd=100),
        broker=broker,
    )
    result = loop.run_cycle(cycle_id="loss-stop", now=NOW)
    assert result.filled_orders == ()
    assert repository.orders == {}
    assert "daily loss limit reached" in result.items[0].risk.reasons


def test_second_distinct_cycle_sees_previous_paper_exposure():
    broker = PaperBroker(initial_cash_usd=1000, fee_bps=0, slippage_bps=0)
    loop, _, _, _ = make_loop(
        candidate=bullish_candidate(),
        settings=enabled_settings(
            paper_default_order_usd=100,
            max_position_usd=100,
            min_cash_reserve_pct=0,
        ),
        broker=broker,
        max_btc_pct=10,
    )
    first = loop.run_cycle(cycle_id="c1", now=NOW)
    second = loop.run_cycle(cycle_id="c2", now=NOW)
    assert len(first.filled_orders) == 1
    assert second.filled_orders == ()
    assert "asset is already at or above its maximum portfolio weight" in second.items[0].risk.reasons
