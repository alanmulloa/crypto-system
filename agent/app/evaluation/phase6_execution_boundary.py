from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ExecutionBoundary:
    spot_only: bool = True
    futures_allowed: bool = False
    margin_allowed: bool = False
    leverage_allowed: bool = False
    withdrawals_allowed: bool = False
    live_orders_allowed: bool = False
    testnet_orders_allowed: bool = False
    private_api_use_allowed: bool = False
    automatic_activation_allowed: bool = False
    phase6_blocked: bool = True


def build_execution_boundary() -> ExecutionBoundary:
    return ExecutionBoundary()


def execution_boundary_to_dict(value: ExecutionBoundary) -> dict[str, Any]:
    return asdict(value)
