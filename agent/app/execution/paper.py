from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum


class PaperSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class PaperOrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class PaperOrderStatus(str, Enum):
    OPEN = "OPEN"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class PaperOrderRequest:
    idempotency_key: str
    symbol: str
    side: PaperSide
    order_type: PaperOrderType
    quantity: float | None = None
    notional_usd: float | None = None
    limit_price: float | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.idempotency_key.strip():
            raise ValueError("idempotency_key is required")
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if (self.quantity is None) == (self.notional_usd is None):
            raise ValueError("exactly one of quantity or notional_usd is required")
        if self.quantity is not None and self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.notional_usd is not None and self.notional_usd <= 0:
            raise ValueError("notional_usd must be positive")
        if self.order_type is PaperOrderType.LIMIT:
            if self.limit_price is None or self.limit_price <= 0:
                raise ValueError("positive limit_price is required for LIMIT orders")
        elif self.limit_price is not None:
            raise ValueError("limit_price is only valid for LIMIT orders")


@dataclass(frozen=True)
class PaperFill:
    order_id: str
    symbol: str
    side: PaperSide
    quantity: float
    price: float
    gross_usd: float
    fee_usd: float
    realized_pnl_usd: float
    filled_at: datetime


@dataclass(frozen=True)
class PaperOrder:
    order_id: str
    request: PaperOrderRequest
    status: PaperOrderStatus
    rejection_reason: str | None = None
    fill: PaperFill | None = None


@dataclass
class PaperPosition:
    symbol: str
    quantity: float = 0.0
    avg_cost_usd: float = 0.0


@dataclass
class PaperAccount:
    cash_usd: float
    positions: dict[str, PaperPosition] = field(default_factory=dict)
    realized_pnl_usd: float = 0.0
    fees_usd: float = 0.0

    def __post_init__(self) -> None:
        if self.cash_usd < 0:
            raise ValueError("cash_usd cannot be negative")

    def position_for(self, symbol: str) -> PaperPosition:
        key = symbol.upper()
        return self.positions.setdefault(key, PaperPosition(symbol=key))


class PaperBroker:
    """Deterministic in-memory broker for paper trading only."""

    def __init__(
        self,
        *,
        initial_cash_usd: float,
        fee_bps: float = 10.0,
        slippage_bps: float = 5.0,
    ):
        if fee_bps < 0 or slippage_bps < 0:
            raise ValueError("fee_bps and slippage_bps cannot be negative")
        self.account = PaperAccount(cash_usd=initial_cash_usd)
        self.fee_bps = fee_bps
        self.slippage_bps = slippage_bps
        self.orders_by_id: dict[str, PaperOrder] = {}
        self.orders_by_key: dict[str, str] = {}
        self._sequence = 0

    def _next_order_id(self) -> str:
        self._sequence += 1
        return f"PAPER-{self._sequence:08d}"

    def _market_crosses_limit(self, request: PaperOrderRequest, market_price: float) -> bool:
        if request.order_type is PaperOrderType.MARKET:
            return True
        if request.side is PaperSide.BUY:
            return market_price <= float(request.limit_price)
        return market_price >= float(request.limit_price)

    def _execution_price(self, request: PaperOrderRequest, market_price: float) -> float:
        if market_price <= 0:
            raise ValueError("market_price must be positive")
        slip = self.slippage_bps / 10_000.0
        if request.side is PaperSide.BUY:
            price = market_price * (1.0 + slip)
            if request.order_type is PaperOrderType.LIMIT:
                price = min(price, float(request.limit_price))
        else:
            price = market_price * (1.0 - slip)
            if request.order_type is PaperOrderType.LIMIT:
                price = max(price, float(request.limit_price))
        return price

    def _reject(self, order: PaperOrder, reason: str) -> PaperOrder:
        rejected = replace(order, status=PaperOrderStatus.REJECTED, rejection_reason=reason)
        self.orders_by_id[order.order_id] = rejected
        return rejected

    def _fill(self, order: PaperOrder, market_price: float, filled_at: datetime) -> PaperOrder:
        request = order.request
        execution_price = self._execution_price(request, market_price)
        if request.quantity is not None:
            quantity = request.quantity
            gross_usd = quantity * execution_price
        else:
            gross_usd = float(request.notional_usd)
            quantity = gross_usd / execution_price

        fee_usd = gross_usd * (self.fee_bps / 10_000.0)
        symbol = request.symbol.upper()
        position = self.account.position_for(symbol)
        realized_pnl = 0.0

        if request.side is PaperSide.BUY:
            cash_required = gross_usd + fee_usd
            if cash_required > self.account.cash_usd + 1e-9:
                return self._reject(order, "insufficient paper cash")
            existing_cost = position.quantity * position.avg_cost_usd
            new_cost = existing_cost + gross_usd + fee_usd
            new_quantity = position.quantity + quantity
            position.quantity = new_quantity
            position.avg_cost_usd = new_cost / new_quantity if new_quantity else 0.0
            self.account.cash_usd -= cash_required
        else:
            if quantity > position.quantity + 1e-12:
                return self._reject(order, "insufficient paper position")
            cost_basis = quantity * position.avg_cost_usd
            net_proceeds = gross_usd - fee_usd
            realized_pnl = net_proceeds - cost_basis
            position.quantity = max(0.0, position.quantity - quantity)
            if position.quantity <= 1e-12:
                position.quantity = 0.0
                position.avg_cost_usd = 0.0
            self.account.cash_usd += net_proceeds
            self.account.realized_pnl_usd += realized_pnl

        self.account.fees_usd += fee_usd
        fill = PaperFill(
            order_id=order.order_id,
            symbol=symbol,
            side=request.side,
            quantity=quantity,
            price=execution_price,
            gross_usd=gross_usd,
            fee_usd=fee_usd,
            realized_pnl_usd=realized_pnl,
            filled_at=filled_at,
        )
        filled = replace(order, status=PaperOrderStatus.FILLED, fill=fill)
        self.orders_by_id[order.order_id] = filled
        return filled

    def submit(
        self,
        request: PaperOrderRequest,
        *,
        market_price: float,
        now: datetime | None = None,
    ) -> PaperOrder:
        if market_price <= 0:
            raise ValueError("market_price must be positive")
        existing_id = self.orders_by_key.get(request.idempotency_key)
        if existing_id:
            existing = self.orders_by_id[existing_id]
            if existing.request != request:
                raise ValueError("idempotency_key was already used for a different request")
            return existing

        order_id = self._next_order_id()
        order = PaperOrder(order_id=order_id, request=request, status=PaperOrderStatus.OPEN)
        self.orders_by_key[request.idempotency_key] = order_id
        self.orders_by_id[order_id] = order

        if not self._market_crosses_limit(request, market_price):
            return order
        return self._fill(order, market_price, now or datetime.now(timezone.utc))

    def process_price(
        self,
        symbol: str,
        *,
        market_price: float,
        now: datetime | None = None,
    ) -> tuple[PaperOrder, ...]:
        filled_at = now or datetime.now(timezone.utc)
        updates: list[PaperOrder] = []
        symbol_upper = symbol.upper()
        for order_id, order in list(self.orders_by_id.items()):
            if order.status is not PaperOrderStatus.OPEN:
                continue
            if order.request.symbol.upper() != symbol_upper:
                continue
            if not self._market_crosses_limit(order.request, market_price):
                continue
            updated = self._fill(order, market_price, filled_at)
            self.orders_by_id[order_id] = updated
            updates.append(updated)
        return tuple(updates)

    def cancel(self, order_id: str) -> PaperOrder:
        order = self.orders_by_id.get(order_id)
        if order is None:
            raise KeyError(order_id)
        if order.status is not PaperOrderStatus.OPEN:
            return order
        cancelled = replace(order, status=PaperOrderStatus.CANCELLED)
        self.orders_by_id[order_id] = cancelled
        return cancelled

    @staticmethod
    def _utc_day(value: datetime):
        return value.astimezone(timezone.utc).date() if value.tzinfo else value.date()

    def daily_realized_pnl(self, day: datetime) -> float:
        target = self._utc_day(day)
        return sum(
            order.fill.realized_pnl_usd
            for order in self.orders_by_id.values()
            if order.fill is not None and self._utc_day(order.fill.filled_at) == target
        )

    def daily_buy_used_usd(self, day: datetime) -> float:
        target = self._utc_day(day)
        return sum(
            order.fill.gross_usd
            for order in self.orders_by_id.values()
            if order.fill is not None
            and order.fill.side is PaperSide.BUY
            and self._utc_day(order.fill.filled_at) == target
        )
