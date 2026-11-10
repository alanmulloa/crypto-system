from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


FROZEN_AT_MS = 1794348615195
FROZEN_SYMBOL = "XRPUSDT"
FROZEN_FEATURE = "volume_ratio_1h"
FROZEN_OPERATOR = "<="
FROZEN_VALUE = 0.75
FROZEN_OUTCOME_HOURS = 24
FROZEN_MIN_MATURED = 20
HOUR_MS = 60 * 60 * 1000


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _observation_key(item: Mapping[str, Any]) -> tuple[str, str, int]:
    return (
        str(item["cohort"]),
        str(item["symbol"]),
        int(item["signal_timestamp_ms"]),
    )


def validate_report(report: Mapping[str, Any]) -> None:
    candidate = report.get("candidate") or {}
    if int(report.get("frozen_at_ms", -1)) != FROZEN_AT_MS:
        raise ValueError("frozen_at_ms changed")
    if candidate.get("symbol") != FROZEN_SYMBOL:
        raise ValueError("candidate symbol changed")
    if candidate.get("feature") != FROZEN_FEATURE:
        raise ValueError("candidate feature changed")
    if candidate.get("operator") != FROZEN_OPERATOR:
        raise ValueError("candidate operator changed")
    if float(candidate.get("value", float("nan"))) != FROZEN_VALUE:
        raise ValueError("candidate threshold changed")
    if int(report.get("outcome_hours", -1)) != FROZEN_OUTCOME_HOURS:
        raise ValueError("outcome_hours changed")
    if int(report.get("min_matured_observations", -1)) != FROZEN_MIN_MATURED:
        raise ValueError("min_matured_observations changed")

    for item in report.get("observations", []):
        signal_ms = int(item["signal_timestamp_ms"])
        if signal_ms <= FROZEN_AT_MS:
            raise ValueError("observation is not strictly post-freeze")
        if item.get("symbol") != FROZEN_SYMBOL:
            raise ValueError("observation symbol changed")
        if item.get("status") != "MATURED":
            continue

        entry_ms = item.get("entry_timestamp_ms")
        outcome_ms = item.get("outcome_timestamp_ms")
        if entry_ms is None or outcome_ms is None:
            raise ValueError("matured observation is missing timestamps")
        required_ms = int(entry_ms) + FROZEN_OUTCOME_HOURS * HOUR_MS - 1
        if int(outcome_ms) < required_ms:
            raise ValueError("matured observation does not have a full 24h outcome")
        if item.get("net_return_pct") is None or item.get("positive_return") is None:
            raise ValueError("matured observation is missing outcome values")


_IMMUTABLE_OBSERVATION_FIELDS = (
    "cohort",
    "symbol",
    "signal_timestamp_ms",
    "entry_timestamp_ms",
    "entry_market_price",
    "feature_value",
)


def assert_history_compatible(
    previous: Mapping[str, Any],
    current: Mapping[str, Any],
) -> None:
    validate_report(previous)
    validate_report(current)

    previous_by_key = {
        _observation_key(item): item for item in previous.get("observations", [])
    }
    current_by_key = {
        _observation_key(item): item for item in current.get("observations", [])
    }

    missing = sorted(set(previous_by_key) - set(current_by_key))
    if missing:
        raise ValueError(f"previous observations disappeared: {missing}")

    for key, old in previous_by_key.items():
        new = current_by_key[key]
        for field in _IMMUTABLE_OBSERVATION_FIELDS:
            if old.get(field) != new.get(field):
                raise ValueError(f"observation mutated immutable field {field}: {key}")

        old_status = old.get("status")
        new_status = new.get("status")
        if old_status == "PENDING" and new_status == "MATURED":
            continue
        if old_status != new_status:
            raise ValueError(f"invalid observation status transition: {key}")

        if old_status == "MATURED":
            for field in (
                "outcome_timestamp_ms",
                "gross_return_pct",
                "net_return_pct",
                "positive_return",
            ):
                if old.get(field) != new.get(field):
                    raise ValueError(f"matured observation mutated {field}: {key}")


def _snapshot_name(report: Mapping[str, Any]) -> str:
    created_at = str((report.get("metadata") or {}).get("created_at") or "")
    if not created_at:
        raise ValueError("metadata.created_at is required")
    safe = created_at.replace(":", "-").replace("+", "_")
    return f"{safe}.json"


def collect(
    *,
    fresh_report: Path,
    latest_report: Path,
    history_dir: Path,
) -> tuple[Path, Path]:
    current = _load(fresh_report)
    validate_report(current)

    if latest_report.exists():
        previous = _load(latest_report)
        assert_history_compatible(previous, current)

    history_dir.mkdir(parents=True, exist_ok=True)
    snapshot = history_dir / _snapshot_name(current)
    serialized = json.dumps(current, indent=2, sort_keys=True, allow_nan=False) + "\n"

    if snapshot.exists() and snapshot.read_text(encoding="utf-8") != serialized:
        raise ValueError(f"immutable snapshot already exists with different content: {snapshot}")

    snapshot.write_text(serialized, encoding="utf-8")
    latest_report.parent.mkdir(parents=True, exist_ok=True)
    latest_report.write_text(serialized, encoding="utf-8")
    return latest_report, snapshot


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5G.1 prospective evidence persistence and integrity gate"
    )
    parser.add_argument("--fresh-report", required=True)
    parser.add_argument("--latest", default="reports/phase5g/latest.json")
    parser.add_argument("--history-dir", default="reports/phase5g/history")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    latest, snapshot = collect(
        fresh_report=Path(args.fresh_report),
        latest_report=Path(args.latest),
        history_dir=Path(args.history_dir),
    )
    print(latest)
    print(snapshot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
