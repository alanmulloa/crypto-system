from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Callable, Protocol

from pydantic import BaseModel, Field

from app.portfolio.models import PortfolioSnapshot
from app.portfolio.tracker_contract import snapshot_from_tracker_rows


class TrackerPortfolioExport(BaseModel):
    schema_version: str = "1.0"
    source_id: str = "crypto_tracker"
    source_revision: str
    generated_at: datetime
    cartera_rows: list[dict[str, object]] = Field(default_factory=list)
    allocation_rows: list[dict[str, object]] = Field(default_factory=list)
    reconciliation_rows: list[dict[str, object]] = Field(default_factory=list)
    daily_buy_used_usd: float = 0.0
    daily_realized_pnl_usd: float = 0.0

    def canonical_json(self) -> str:
        return json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    def content_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def to_snapshot(self, *, cash_asset: str = "USDC") -> PortfolioSnapshot:
        return snapshot_from_tracker_rows(
            cartera_rows=self.cartera_rows,
            allocation_rows=self.allocation_rows,
            reconciliation_rows=self.reconciliation_rows,
            cash_asset=cash_asset,
            daily_buy_used_usd=self.daily_buy_used_usd,
            daily_realized_pnl_usd=self.daily_realized_pnl_usd,
        )


@dataclass(frozen=True)
class SyncMetadata:
    content_hash: str
    generated_at: datetime


class PortfolioSyncRepository(Protocol):
    def latest_metadata(self, source_id: str) -> SyncMetadata | None: ...

    def save(
        self,
        export: TrackerPortfolioExport,
        snapshot: PortfolioSnapshot,
        content_hash: str,
    ) -> None: ...


class SyncState(str, Enum):
    APPLIED = "APPLIED"
    DUPLICATE = "DUPLICATE"
    STALE = "STALE"


@dataclass(frozen=True)
class PortfolioSyncResult:
    state: SyncState
    content_hash: str
    generated_at: datetime
    total_value_usd: float
    cash_value_usd: float
    capital_at_risk_usd: float
    reason: str


class PortfolioSyncService:
    def __init__(
        self,
        repository: PortfolioSyncRepository,
        *,
        cash_asset: str = "USDC",
        max_age_minutes: int = 30,
        future_tolerance_minutes: int = 5,
        now: Callable[[], datetime] | None = None,
    ):
        if max_age_minutes <= 0:
            raise ValueError("max_age_minutes must be positive")
        self.repository = repository
        self.cash_asset = cash_asset
        self.max_age = timedelta(minutes=max_age_minutes)
        self.future_tolerance = timedelta(minutes=future_tolerance_minutes)
        self.now = now or (lambda: datetime.now(timezone.utc))

    def sync(self, export: TrackerPortfolioExport) -> PortfolioSyncResult:
        generated_at = export.generated_at
        if generated_at.tzinfo is None:
            generated_at = generated_at.replace(tzinfo=timezone.utc)
        else:
            generated_at = generated_at.astimezone(timezone.utc)

        now = self.now()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        else:
            now = now.astimezone(timezone.utc)

        content_hash = export.content_hash()
        snapshot = export.to_snapshot(cash_asset=self.cash_asset)
        latest = self.repository.latest_metadata(export.source_id)

        if latest and latest.content_hash == content_hash:
            return PortfolioSyncResult(
                state=SyncState.DUPLICATE,
                content_hash=content_hash,
                generated_at=generated_at,
                total_value_usd=snapshot.total_value_usd,
                cash_value_usd=snapshot.cash_value_usd,
                capital_at_risk_usd=snapshot.capital_at_risk_usd,
                reason="identical snapshot already stored",
            )

        if latest:
            latest_at = latest.generated_at
            if latest_at.tzinfo is None:
                latest_at = latest_at.replace(tzinfo=timezone.utc)
            if generated_at <= latest_at:
                return PortfolioSyncResult(
                    state=SyncState.STALE,
                    content_hash=content_hash,
                    generated_at=generated_at,
                    total_value_usd=snapshot.total_value_usd,
                    cash_value_usd=snapshot.cash_value_usd,
                    capital_at_risk_usd=snapshot.capital_at_risk_usd,
                    reason="snapshot is older than or equal to the latest stored snapshot",
                )

        if generated_at > now + self.future_tolerance:
            return PortfolioSyncResult(
                state=SyncState.STALE,
                content_hash=content_hash,
                generated_at=generated_at,
                total_value_usd=snapshot.total_value_usd,
                cash_value_usd=snapshot.cash_value_usd,
                capital_at_risk_usd=snapshot.capital_at_risk_usd,
                reason="snapshot timestamp is unexpectedly in the future",
            )

        if now - generated_at > self.max_age:
            return PortfolioSyncResult(
                state=SyncState.STALE,
                content_hash=content_hash,
                generated_at=generated_at,
                total_value_usd=snapshot.total_value_usd,
                cash_value_usd=snapshot.cash_value_usd,
                capital_at_risk_usd=snapshot.capital_at_risk_usd,
                reason="snapshot exceeds maximum accepted age",
            )

        self.repository.save(export, snapshot, content_hash)
        return PortfolioSyncResult(
            state=SyncState.APPLIED,
            content_hash=content_hash,
            generated_at=generated_at,
            total_value_usd=snapshot.total_value_usd,
            cash_value_usd=snapshot.cash_value_usd,
            capital_at_risk_usd=snapshot.capital_at_risk_usd,
            reason="snapshot stored",
        )
