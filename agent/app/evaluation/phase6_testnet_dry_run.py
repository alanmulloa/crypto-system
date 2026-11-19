from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.config import Settings
from app.evaluation.phase6_readiness import Phase6Readiness


@dataclass(frozen=True)
class TestnetDryRunPlan:
    state: str
    trading_mode_required: str
    binance_testnet_required: bool
    kill_switch_required: bool
    max_position_usd: float
    max_daily_buy_usd: float
    max_open_positions: int
    daily_loss_limit_usd: float
    private_api_calls: bool
    orders_submitted: bool
    credentials_written: bool
    phase6_blocked: bool
    detail: str


def build_testnet_dry_run_plan(
    *,
    readiness: Phase6Readiness,
    settings: Settings,
) -> TestnetDryRunPlan:
    allowed = readiness.state == "APPROVED_FOR_TESTNET_PREPARATION"
    return TestnetDryRunPlan(
        state="DRY_RUN_PLAN_READY" if allowed else "DRY_RUN_PLAN_BLOCKED",
        trading_mode_required="TESTNET",
        binance_testnet_required=True,
        kill_switch_required=True,
        max_position_usd=settings.max_position_usd,
        max_daily_buy_usd=settings.max_daily_buy_usd,
        max_open_positions=settings.max_open_positions,
        daily_loss_limit_usd=settings.daily_loss_limit_usd,
        private_api_calls=False,
        orders_submitted=False,
        credentials_written=False,
        phase6_blocked=True,
        detail=(
            "Plan is informational only; no mode change, credentials or orders occur."
            if allowed
            else "Readiness approval is incomplete; dry-run preparation is blocked."
        ),
    )


def dry_run_plan_to_dict(value: TestnetDryRunPlan) -> dict[str, Any]:
    return asdict(value)
