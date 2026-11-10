import pytest
from datetime import datetime, timezone

from app.execution import (
    PaperBroker,
    PaperOrderRequest,
    PaperOrderStatus,
    PaperOrderType,
    PaperSide,
)


NOW = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)


def test_market_buy_applies_deterministic_slippage_and_fee():
    broker = PaperBroker(initial_cash_usd=1000, fee_bps=10, slippage_bps=50)
    order = broker.submit(
        PaperOrderRequest(
            idempotency_key="buy-1",
            symbol="BTCUSDT",
            side=PaperSide.BUY,
            order_type=PaperOrderType.MARKET,
            notional_usd=100,
        ),
        market_price=100,
        now=NOW,
    )
    assert order.status is PaperOrderStatus.FILLED
    assert order.fill is not None
    assert order.fill.price == pytest.approx(100.5)
    assert order.fill.fee_usd == pytest.approx(0.1)
    assert broker.account.cash_usd == pytest.approx(899.9)
    assert broker.account.position_for("BTCUSDT").quantity > 0


def test_sell_realizes_pnl_and_resets_closed_position():
    broker = PaperBroker(initial_cash_usd=1000, fee_bps=0, slippage_bps=0)
    buy = broker.submit(
        PaperOrderRequest(
            idempotency_key="buy",
            symbol="ETHUSDT",
            side=PaperSide.BUY,
            order_type=PaperOrderType.MARKET,
            quantity=2,
        ),
        market_price=100,
        now=NOW,
    )
    assert buy.status is PaperOrderStatus.FILLED

    sell = broker.submit(
        PaperOrderRequest(
            idempotency_key="sell",
            symbol="ETHUSDT",
            side=PaperSide.SELL,
            order_type=PaperOrderType.MARKET,
            quantity=2,
        ),
        market_price=120,
        now=NOW,
    )
    assert sell.status is PaperOrderStatus.FILLED
    assert sell.fill is not None
    assert sell.fill.realized_pnl_usd == pytest.approx(40)
    assert broker.account.realized_pnl_usd == pytest.approx(40)
    assert broker.account.position_for("ETHUSDT").quantity == 0
    assert broker.daily_realized_pnl(NOW) == pytest.approx(40)


def test_idempotent_submit_returns_same_order_without_double_fill():
    broker = PaperBroker(initial_cash_usd=1000, fee_bps=0, slippage_bps=0)
    request = PaperOrderRequest(
        idempotency_key="same",
        symbol="BTCUSDT",
        side=PaperSide.BUY,
        order_type=PaperOrderType.MARKET,
        notional_usd=100,
    )
    first = broker.submit(request, market_price=100, now=NOW)
    cash_after_first = broker.account.cash_usd
    second = broker.submit(request, market_price=200, now=NOW)
    assert second.order_id == first.order_id
    assert broker.account.cash_usd == cash_after_first


def test_idempotency_key_cannot_be_reused_for_different_request():
    broker = PaperBroker(initial_cash_usd=1000)
    broker.submit(
        PaperOrderRequest(
            idempotency_key="key",
            symbol="BTCUSDT",
            side=PaperSide.BUY,
            order_type=PaperOrderType.MARKET,
            notional_usd=100,
        ),
        market_price=100,
        now=NOW,
    )
    try:
        broker.submit(
            PaperOrderRequest(
                idempotency_key="key",
                symbol="BTCUSDT",
                side=PaperSide.BUY,
                order_type=PaperOrderType.MARKET,
                notional_usd=200,
            ),
            market_price=100,
            now=NOW,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("expected idempotency conflict")


def test_limit_buy_remains_open_until_market_crosses_limit():
    broker = PaperBroker(initial_cash_usd=1000, fee_bps=0, slippage_bps=0)
    order = broker.submit(
        PaperOrderRequest(
            idempotency_key="limit-buy",
            symbol="BTCUSDT",
            side=PaperSide.BUY,
            order_type=PaperOrderType.LIMIT,
            notional_usd=100,
            limit_price=95,
        ),
        market_price=100,
        now=NOW,
    )
    assert order.status is PaperOrderStatus.OPEN
    assert broker.process_price("BTCUSDT", market_price=96, now=NOW) == ()
    updates = broker.process_price("BTCUSDT", market_price=94, now=NOW)
    assert len(updates) == 1
    assert updates[0].status is PaperOrderStatus.FILLED
    assert updates[0].fill.price == pytest.approx(94)


def test_limit_price_caps_adverse_slippage():
    broker = PaperBroker(initial_cash_usd=1000, fee_bps=0, slippage_bps=200)
    order = broker.submit(
        PaperOrderRequest(
            idempotency_key="limit-cap",
            symbol="BTCUSDT",
            side=PaperSide.BUY,
            order_type=PaperOrderType.LIMIT,
            notional_usd=100,
            limit_price=100,
        ),
        market_price=99,
        now=NOW,
    )
    assert order.fill is not None
    assert order.fill.price == pytest.approx(100)


def test_sell_cannot_exceed_paper_position():
    broker = PaperBroker(initial_cash_usd=1000, fee_bps=0, slippage_bps=0)
    order = broker.submit(
        PaperOrderRequest(
            idempotency_key="bad-sell",
            symbol="BTCUSDT",
            side=PaperSide.SELL,
            order_type=PaperOrderType.MARKET,
            quantity=1,
        ),
        market_price=100,
        now=NOW,
    )
    assert order.status is PaperOrderStatus.REJECTED
    assert order.rejection_reason == "insufficient paper position"


def test_insufficient_cash_rejects_buy_without_mutating_account():
    broker = PaperBroker(initial_cash_usd=50, fee_bps=0, slippage_bps=0)
    order = broker.submit(
        PaperOrderRequest(
            idempotency_key="too-big",
            symbol="BTCUSDT",
            side=PaperSide.BUY,
            order_type=PaperOrderType.MARKET,
            notional_usd=100,
        ),
        market_price=100,
        now=NOW,
    )
    assert order.status is PaperOrderStatus.REJECTED
    assert broker.account.cash_usd == pytest.approx(50)
    assert broker.account.position_for("BTCUSDT").quantity == 0


def test_open_limit_order_can_be_cancelled():
    broker = PaperBroker(initial_cash_usd=1000)
    order = broker.submit(
        PaperOrderRequest(
            idempotency_key="cancel-me",
            symbol="BTCUSDT",
            side=PaperSide.BUY,
            order_type=PaperOrderType.LIMIT,
            notional_usd=100,
            limit_price=90,
        ),
        market_price=100,
        now=NOW,
    )
    cancelled = broker.cancel(order.order_id)
    assert cancelled.status is PaperOrderStatus.CANCELLED
