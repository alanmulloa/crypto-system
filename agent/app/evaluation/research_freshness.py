from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping


DEFAULT_MAX_AGE_HOURS = 12.0


def _parse_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class EvidenceFreshness:
    state: str
    source_created_at: str | None
    age_hours: float | None
    max_age_hours: float
    fresh: bool
    detail: str


def evaluate_freshness(
    report: Mapping[str, Any] | None,
    *,
    as_of: datetime,
    max_age_hours: float = DEFAULT_MAX_AGE_HOURS,
) -> EvidenceFreshness:
    if max_age_hours <= 0:
        raise ValueError("max_age_hours must be positive")
    now = as_of.astimezone(timezone.utc)

    if report is None:
        return EvidenceFreshness(
            state="MISSING",
            source_created_at=None,
            age_hours=None,
            max_age_hours=max_age_hours,
            fresh=False,
            detail="No latest evidence artifact is available.",
        )

    metadata = report.get("metadata") or {}
    created_at = metadata.get("created_at")
    if not isinstance(created_at, str) or not created_at:
        return EvidenceFreshness(
            state="MISSING_TIMESTAMP",
            source_created_at=None,
            age_hours=None,
            max_age_hours=max_age_hours,
            fresh=False,
            detail="Evidence artifact has no metadata.created_at timestamp.",
        )

    source_time = _parse_iso(created_at)
    age_hours = max(0.0, (now - source_time).total_seconds() / 3600.0)
    fresh = age_hours <= max_age_hours
    return EvidenceFreshness(
        state="FRESH" if fresh else "STALE",
        source_created_at=created_at,
        age_hours=age_hours,
        max_age_hours=max_age_hours,
        fresh=fresh,
        detail=(
            "Latest evidence is within the freshness window."
            if fresh
            else "Latest evidence exceeds the freshness window."
        ),
    )


def freshness_to_dict(value: EvidenceFreshness) -> dict[str, Any]:
    return asdict(value)
