from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class HumanApproval:
    experiment_id: str
    scope: str
    approved: bool
    approver: str | None
    approved_at: str | None
    note: str | None
    allows_testnet_preparation: bool
    allows_testnet_orders: bool
    allows_live_orders: bool


def build_pending_approval(experiment_id: str) -> HumanApproval:
    return HumanApproval(
        experiment_id=experiment_id,
        scope="TESTNET_PREPARATION_ONLY",
        approved=False,
        approver=None,
        approved_at=None,
        note=None,
        allows_testnet_preparation=False,
        allows_testnet_orders=False,
        allows_live_orders=False,
    )


def approve_testnet_preparation(
    *,
    experiment_id: str,
    approver: str,
    note: str | None = None,
    approved_at: datetime | None = None,
) -> HumanApproval:
    if not approver.strip():
        raise ValueError("approver is required")
    timestamp = (approved_at or datetime.now(timezone.utc)).astimezone(
        timezone.utc
    )
    return HumanApproval(
        experiment_id=experiment_id,
        scope="TESTNET_PREPARATION_ONLY",
        approved=True,
        approver=approver.strip(),
        approved_at=timestamp.isoformat(),
        note=note,
        allows_testnet_preparation=True,
        allows_testnet_orders=False,
        allows_live_orders=False,
    )


def approval_to_dict(value: HumanApproval) -> dict[str, Any]:
    return asdict(value)
