from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Protocol
from urllib.request import Request, urlopen

from app.market.types import MarketCandidate


class MarketRepository(Protocol):
    def save_candidates(self, candidates: list[MarketCandidate]) -> None: ...


class NullMarketRepository:
    """Default repository for local development/tests; performs no network I/O."""

    def save_candidates(self, candidates: list[MarketCandidate]) -> None:
        return None


class SupabaseMarketRepository:
    """Optional Phase 1 persistence adapter using Supabase REST.

    It is never created implicitly, so tests and local scans do not require credentials.
    The service-role key belongs only on the backend/runtime, never in GitHub or the UI.
    """

    def __init__(self, url: str, service_role_key: str, timeout_seconds: float = 10.0):
        if not url or not service_role_key:
            raise ValueError("Supabase URL and service-role key are required")
        self.url = url.rstrip("/")
        self.key = service_role_key
        self.timeout_seconds = timeout_seconds

    def save_candidates(self, candidates: list[MarketCandidate]) -> None:
        observed_at = datetime.now(timezone.utc).isoformat()
        rows = []
        for candidate in candidates:
            payload = asdict(candidate)
            rows.append(
                {
                    "symbol": candidate.symbol,
                    "ranking_score": candidate.ranking_score,
                    "quote_volume_24h": candidate.quote_volume_24h,
                    "payload": payload,
                    "observed_at": observed_at,
                }
            )
        if not rows:
            return
        request = Request(
            f"{self.url}/rest/v1/market_candidates",
            data=json.dumps(rows, default=lambda value: getattr(value, "value", str(value))).encode("utf-8"),
            headers={
                "apikey": self.key,
                "Authorization": f"Bearer {self.key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            method="POST",
        )
        with urlopen(request, timeout=self.timeout_seconds):  # noqa: S310 - operator-configured Supabase URL
            pass
