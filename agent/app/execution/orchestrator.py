from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.execution.paper import (
    PaperBroker,
    PaperOrder,
    PaperOrderRequest,
    PaperOrderStatus,
    PaperOrderType,
    PaperSide,
)
from app.risk.portfolio import PortfolioRiskDecision, RiskState


from enum import Enum


class ExecutionIntentSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    REDUCE = "REDUCE"


@dataclass(frozen=True)
class PaperExecutionIntent:
    idempotency_key: str
    symbol: str
    side: ExecutionIntentSide
    requested_notional_usd: float
    order_type: PaperOrderType = PaperOrderType.MARKET
    limit_price: float | None = None

    def __post_init__(self) -> None:
        if not self.idempotency_key.strip():
            raise ValueError("idempotency_key is required")
        if self.requested_notional_usd <= 0:
            raise ValueError("requested_notional_usd must be positive")
        if self.order_type is PaperOrderType.LIMIT:
            if self.limit_price is None or self.limit_price <= 0:
                raise ValueError("LIMIT intent requires a positive limit_price")
        elif self.limit_price is not None:
            raise ValueError("limit_price is only valid for LIMIT intent")
        if self.side is ExecutionIntentSide.REDUCE and self.order_type is PaperOrderType.LIMIT:
            raise ValueError("REDUCE intent must use MARKET order type")


class PaperExecutionRepository(Protocol):
    def find_by_idempotency_key(self, key: str) -> PaperOrder | None: ...

    def save_order(self, order: PaperOrder, *, risk: PortfolioRiskDecision) -> None: ...


class NullPaperExecutionRepository:
    def find_by_idempotency_key(self, key: str) -> PaperOrder | None:
        return None

    def save_order(self, order: PaperOrder, *, risk: PortfolioRiskDecision) -> None:
        return None


class InMemoryPaperExecutionRepository:
    def __init__(self):
        self.orders: dict[str, PaperOrder] = {}
        self.risk_by_key: dict[str, PortfolioRiskDecision] = {}

    def find_by_idempotency_key(self, key: str) -> PaperOrder | None:
        return self.orders.get(key)

    def save_order(self, order: PaperOrder, *, risk: PortfolioRiskDecision) -> None:
        key = order.request.idempotency_key
        self.orders[key] = order
        self.risk_by_key[key] = risk


class PaperExecutionOrchestrator:
    """Risk-gated bridge into the deterministic PaperBroker.

    Supports BUY, SELL, and REDUCE intents for paper trading.
    Cannot bypass PortfolioRiskDecision and has no real broker/network integration.
    """

    def __init__(
        self,
        broker: PaperBroker,
        repository: PaperExecutionRepository | None = None,
    ):
        self.broker = broker
        self.repository = repository or NullPaperExecutionRepository()

    def execute(
        self,
        *,
        intent: PaperExecutionIntent,
        risk: PortfolioRiskDecision,
        market_price: float,
        now: datetime | None = None,
    ) -> PaperOrder:
        existing = self.repository.find_by_idempotency_key(intent.idempotency_key)
        if existing is not None:
            if (
                existing.request.symbol.upper() != intent.symbol.upper()
                or existing.request.side.value != intent.side.value
                or existing.request.notional_usd != min(intent.requested_notional_usd, risk.max_notional_usd)
                or existing.request.order_type is not intent.order_type
                or existing.request.limit_price != intent.limit_price
            ):
                raise ValueError("idempotency_key already persisted for different execution intent")
            return existing

        if not risk.approved or risk.state is not RiskState.APPROVED:
            raise PermissionError("paper execution requires an approved risk decision")
        if risk.symbol.upper() != intent.symbol.upper():
            raise ValueError("risk decision symbol does not match execution intent")
        if risk.max_notional_usd <= 0:
            raise PermissionError("approved risk decision has no notional capacity")

        authorized_notional = min(intent.requested_notional_usd, risk.max_notional_usd)

        # Map execution intent side to paper broker side
        paper_side = (
            PaperSide.BUY
            if intent.side is ExecutionIntentSide.BUY
            else PaperSide.SELL
        )

        request = PaperOrderRequest(
            idempotency_key=intent.idempotency_key,
            symbol=intent.symbol.upper(),
            side=paper_side,
            order_type=intent.order_type,
            notional_usd=authorized_notional,
            limit_price=intent.limit_price,
            created_at=now or intent_time(intent),
        )

        order = self.broker.submit(
            request,
            market_price=market_price,
            now=now,
        )
        self.repository.save_order(order, risk=risk)
        return order

    def persist_update(
        self,
        order: PaperOrder,
        *,
        risk: PortfolioRiskDecision,
    ) -> None:
        if order.status not in {
            PaperOrderStatus.OPEN,
            PaperOrderStatus.FILLED,
            PaperOrderStatus.REJECTED,
            PaperOrderStatus.CANCELLED,
        }:
            raise ValueError("unsupported paper order status")
        self.repository.save_order(order, risk=risk)


def intent_time(intent: PaperExecutionIntent) -> datetime:
    # Kept separate for deterministic testing/injection by caller. PaperOrderRequest
    # itself supplies UTC now when the orchestrator caller does not pass a timestamp.
    paper_side = (
        PaperSide.BUY
        if intent.side is ExecutionIntentSide.BUY
        else PaperSide.SELL
    )
    return PaperOrderRequest(
        idempotency_key=f"{intent.idempotency_key}:clock",
        symbol=intent.symbol,
        side=paper_side,
        order_type=PaperOrderType.MARKET,
        notional_usd=1.0,
    ).created_at
