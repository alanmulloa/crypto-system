from datetime import datetime, timezone

import pytest

from app.execution import (
    InMemoryPaperExecutionRepository,
    PaperBroker,
    PaperExecutionIntent,
    PaperExecutionOrchestrator,
    PaperOrderStatus,
    PaperOrderType,
)
from app.risk import PortfolioRiskDecision, RiskState


NOW = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)


def risk(*, approved=True, max_notional=250, symbol="BTCUSDT"):
    return PortfolioRiskDecision(
        symbol=symbol,
        state=RiskState.APPROVED if approved else RiskState.BLOCKED,
        approved=approved,
        max_notional_usd=max_notional if approved else 0,
        reasons=() if approved else ("blocked",),
    )


def test_requires_explicit_risk_approval():
    broker = PaperBroker(initial_cash_usd=1000, fee_bps=0, slippage_bps=0)
    orchestrator = PaperExecutionOrchestrator(broker)
    with pytest.raises(PermissionError):
        orchestrator.execute(
            intent=PaperExecutionIntent("x", "BTCUSDT", 100),
            risk=risk(approved=False),
            market_price=100,
            now=NOW,
        )
    assert broker.account.cash_usd == 1000


def test_authorized_notional_is_capped_by_risk_decision():
    broker = PaperBroker(initial_cash_usd=1000, fee_bps=0, slippage_bps=0)
    repository = InMemoryPaperExecutionRepository()
    orchestrator = PaperExecutionOrchestrator(broker, repository)
    order = orchestrator.execute(
        intent=PaperExecutionIntent("x", "BTCUSDT", 400),
        risk=risk(max_notional=250),
        market_price=100,
        now=NOW,
    )
    assert order.status is PaperOrderStatus.FILLED
    assert order.request.notional_usd == 250
    assert broker.account.cash_usd == pytest.approx(750)
    assert repository.find_by_idempotency_key("x") == order


def test_risk_symbol_must_match_intent():
    broker = PaperBroker(initial_cash_usd=1000)
    orchestrator = PaperExecutionOrchestrator(broker)
    with pytest.raises(ValueError):
        orchestrator.execute(
            intent=PaperExecutionIntent("x", "ETHUSDT", 100),
            risk=risk(symbol="BTCUSDT"),
            market_price=100,
            now=NOW,
        )


def test_persisted_idempotency_prevents_restart_double_fill():
    repository = InMemoryPaperExecutionRepository()
    first_broker = PaperBroker(initial_cash_usd=1000, fee_bps=0, slippage_bps=0)
    first = PaperExecutionOrchestrator(first_broker, repository)
    intent = PaperExecutionIntent("restart-safe", "BTCUSDT", 100)

    original = first.execute(
        intent=intent,
        risk=risk(),
        market_price=100,
        now=NOW,
    )

    # Simulate process restart: new broker instance but same durable repository.
    second_broker = PaperBroker(initial_cash_usd=1000, fee_bps=0, slippage_bps=0)
    second = PaperExecutionOrchestrator(second_broker, repository)
    replay = second.execute(
        intent=intent,
        risk=risk(),
        market_price=200,
        now=NOW,
    )

    assert replay == original
    assert second_broker.account.cash_usd == 1000


def test_same_idempotency_key_with_changed_intent_is_rejected():
    repository = InMemoryPaperExecutionRepository()
    broker = PaperBroker(initial_cash_usd=1000, fee_bps=0, slippage_bps=0)
    orchestrator = PaperExecutionOrchestrator(broker, repository)
    orchestrator.execute(
        intent=PaperExecutionIntent("same", "BTCUSDT", 100),
        risk=risk(),
        market_price=100,
        now=NOW,
    )
    with pytest.raises(ValueError):
        orchestrator.execute(
            intent=PaperExecutionIntent("same", "BTCUSDT", 200),
            risk=risk(),
            market_price=100,
            now=NOW,
        )


def test_limit_intent_is_authorized_but_can_remain_open():
    broker = PaperBroker(initial_cash_usd=1000, fee_bps=0, slippage_bps=0)
    repository = InMemoryPaperExecutionRepository()
    orchestrator = PaperExecutionOrchestrator(broker, repository)
    order = orchestrator.execute(
        intent=PaperExecutionIntent(
            "limit",
            "BTCUSDT",
            100,
            PaperOrderType.LIMIT,
            90,
        ),
        risk=risk(),
        market_price=100,
        now=NOW,
    )
    assert order.status is PaperOrderStatus.OPEN
    assert repository.find_by_idempotency_key("limit") == order
