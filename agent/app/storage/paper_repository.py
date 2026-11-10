from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.execution.paper import (
    PaperFill,
    PaperOrder,
    PaperOrderRequest,
    PaperOrderStatus,
    PaperOrderType,
    PaperSide,
)
from app.execution.orchestrator import PaperExecutionRepository
from app.risk.portfolio import PortfolioRiskDecision


class SupabasePaperExecutionRepository(PaperExecutionRepository):
    """Persistence adapter for paper orders/fills only.

    Uses backend service-role credentials and never talks to Binance.
    """

    def __init__(self, url: str, service_role_key: str, timeout_seconds: float = 10.0):
        if not url or not service_role_key:
            raise ValueError("Supabase URL and service-role key are required")
        self.url = url.rstrip("/")
        self.key = service_role_key
        self.timeout_seconds = timeout_seconds

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }

    def _get_rows(self, table: str, params: dict[str, str]) -> list[dict[str, Any]]:
        query = urlencode(params)
        request = Request(
            f"{self.url}/rest/v1/{table}?{query}",
            headers=self._headers,
            method="GET",
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))

    def find_by_idempotency_key(self, key: str) -> PaperOrder | None:
        rows = self._get_rows(
            "orders",
            {
                "broker": "eq.PAPER",
                "idempotency_key": f"eq.{key}",
                "select": "*",
                "limit": "1",
            },
        )
        if not rows:
            return None
        row = rows[0]
        request = PaperOrderRequest(
            idempotency_key=str(row["idempotency_key"]),
            symbol=str(row["symbol"]),
            side=PaperSide(str(row["side"])),
            order_type=PaperOrderType(str(row["order_type"])),
            quantity=float(row["quantity"]) if row.get("quantity") is not None else None,
            notional_usd=float(row["notional_usd"]) if row.get("notional_usd") is not None else None,
            limit_price=float(row["limit_price"]) if row.get("limit_price") is not None else None,
            created_at=datetime.fromisoformat(str(row["created_at"]).replace("Z", "+00:00")),
        )
        fill = self._load_fill(str(row["id"])) if row.get("status") == PaperOrderStatus.FILLED.value else None
        return PaperOrder(
            order_id=str(row["external_order_id"] or row["id"]),
            request=request,
            status=PaperOrderStatus(str(row["status"])),
            rejection_reason=(row.get("raw") or {}).get("rejection_reason"),
            fill=fill,
        )

    def _load_fill(self, db_order_id: str) -> PaperFill | None:
        rows = self._get_rows(
            "fills",
            {
                "order_id": f"eq.{db_order_id}",
                "select": "*",
                "limit": "1",
            },
        )
        if not rows:
            return None
        row = rows[0]
        raw = row.get("raw") or {}
        return PaperFill(
            order_id=str(raw.get("paper_order_id") or db_order_id),
            symbol=str(raw.get("symbol") or ""),
            side=PaperSide(str(raw.get("side") or "BUY")),
            quantity=float(row["quantity"]),
            price=float(row["price"]),
            gross_usd=float(raw.get("gross_usd") or 0.0),
            fee_usd=float(row.get("fee_usd") or 0.0),
            realized_pnl_usd=float(row.get("realized_pnl_usd") or 0.0),
            filled_at=datetime.fromisoformat(str(row["filled_at"]).replace("Z", "+00:00")),
        )

    def save_order(self, order: PaperOrder, *, risk: PortfolioRiskDecision) -> None:
        row = {
            "broker": "PAPER",
            "external_order_id": order.order_id,
            "idempotency_key": order.request.idempotency_key,
            "symbol": order.request.symbol,
            "side": order.request.side.value,
            "order_type": order.request.order_type.value,
            "quantity": order.request.quantity,
            "notional_usd": order.request.notional_usd,
            "limit_price": order.request.limit_price,
            "status": order.status.value,
            "risk_snapshot": {
                "state": risk.state.value,
                "approved": risk.approved,
                "max_notional_usd": risk.max_notional_usd,
                "reasons": list(risk.reasons),
            },
            "raw": {
                "rejection_reason": order.rejection_reason,
            },
            "created_at": order.request.created_at.isoformat(),
            "updated_at": datetime.now().astimezone().isoformat(),
        }
        request = Request(
            f"{self.url}/rest/v1/orders?on_conflict=broker,idempotency_key",
            data=json.dumps(row).encode("utf-8"),
            headers={
                **self._headers,
                "Prefer": "resolution=merge-duplicates,return=representation",
            },
            method="POST",
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
            saved = json.loads(response.read().decode("utf-8"))
        if not saved:
            return
        db_order_id = str(saved[0]["id"])

        if order.fill is not None:
            fill_row = {
                "order_id": db_order_id,
                "price": order.fill.price,
                "quantity": order.fill.quantity,
                "fee_usd": order.fill.fee_usd,
                "realized_pnl_usd": order.fill.realized_pnl_usd,
                "filled_at": order.fill.filled_at.isoformat(),
                "raw": {
                    "paper_order_id": order.fill.order_id,
                    "symbol": order.fill.symbol,
                    "side": order.fill.side.value,
                    "gross_usd": order.fill.gross_usd,
                },
            }
            fill_request = Request(
                f"{self.url}/rest/v1/fills?on_conflict=order_id",
                data=json.dumps(fill_row).encode("utf-8"),
                headers={
                    **self._headers,
                    "Prefer": "resolution=merge-duplicates,return=minimal",
                },
                method="POST",
            )
            with urlopen(fill_request, timeout=self.timeout_seconds):  # noqa: S310
                pass
