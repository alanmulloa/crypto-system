from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.portfolio.models import PortfolioSnapshot
from app.portfolio.sync import PortfolioSyncRepository, SyncMetadata, TrackerPortfolioExport


class InMemoryPortfolioSyncRepository(PortfolioSyncRepository):
    def __init__(self):
        self.records: list[tuple[TrackerPortfolioExport, PortfolioSnapshot, str]] = []

    def latest_metadata(self, source_id: str) -> SyncMetadata | None:
        matches = [
            item
            for item in self.records
            if item[0].source_id == source_id
        ]
        if not matches:
            return None
        export, _, content_hash = max(matches, key=lambda item: item[0].generated_at)
        return SyncMetadata(content_hash=content_hash, generated_at=export.generated_at)

    def save(
        self,
        export: TrackerPortfolioExport,
        snapshot: PortfolioSnapshot,
        content_hash: str,
    ) -> None:
        self.records.append((export, snapshot, content_hash))


class SupabasePortfolioSyncRepository(PortfolioSyncRepository):
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

    def latest_metadata(self, source_id: str) -> SyncMetadata | None:
        query = urlencode(
            {
                "source_id": f"eq.{source_id}",
                "select": "content_hash,generated_at",
                "order": "generated_at.desc",
                "limit": "1",
            }
        )
        request = Request(
            f"{self.url}/rest/v1/portfolio_syncs?{query}",
            headers=self._headers,
            method="GET",
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
            rows: list[dict[str, Any]] = json.loads(response.read().decode("utf-8"))
        if not rows:
            return None
        return SyncMetadata(
            content_hash=str(rows[0]["content_hash"]),
            generated_at=datetime.fromisoformat(str(rows[0]["generated_at"]).replace("Z", "+00:00")),
        )

    def save(
        self,
        export: TrackerPortfolioExport,
        snapshot: PortfolioSnapshot,
        content_hash: str,
    ) -> None:
        payload = {
            "schema_version": export.schema_version,
            "source_id": export.source_id,
            "source_revision": export.source_revision,
            "content_hash": content_hash,
            "generated_at": export.generated_at.isoformat(),
            "total_value_usd": snapshot.total_value_usd,
            "cash_value_usd": snapshot.cash_value_usd,
            "capital_at_risk_usd": snapshot.capital_at_risk_usd,
            "snapshot": asdict(snapshot),
            "raw_payload": export.model_dump(mode="json"),
        }
        request = Request(
            f"{self.url}/rest/v1/portfolio_syncs",
            data=json.dumps(payload, default=lambda value: getattr(value, "value", str(value))).encode("utf-8"),
            headers={**self._headers, "Prefer": "return=minimal"},
            method="POST",
        )
        with urlopen(request, timeout=self.timeout_seconds):  # noqa: S310
            pass
