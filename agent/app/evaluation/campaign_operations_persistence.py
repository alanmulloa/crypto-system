from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


def _snapshot_name(report: Mapping[str, Any]) -> str:
    generated_at = str(report.get("generated_at") or "")
    if not generated_at:
        raise ValueError("generated_at is required")
    return generated_at.replace(":", "-").replace("+", "_") + ".json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def persist_campaign_operations(
    *,
    fresh_report: Path,
    latest_report: Path,
    history_dir: Path,
) -> tuple[Path, Path]:
    current = _load(fresh_report)
    if current.get("phase") != "5L.5":
        raise ValueError("campaign operations report must be Phase 5L.5")
    if current.get("research_only") is not True:
        raise ValueError("campaign operations report must be research_only")
    if current.get("phase6_blocked") is not True:
        raise ValueError("campaign operations report must keep Phase 6 blocked")

    if latest_report.exists():
        previous = _load(latest_report)
        if (
            previous.get("campaign_fingerprint_sha256")
            != current.get("campaign_fingerprint_sha256")
        ):
            raise ValueError("campaign fingerprint drift detected")
        old_time = str(previous.get("generated_at") or "")
        new_time = str(current.get("generated_at") or "")
        if new_time <= old_time:
            raise ValueError("campaign operations time did not advance")

    history_dir.mkdir(parents=True, exist_ok=True)
    snapshot = history_dir / _snapshot_name(current)
    serialized = json.dumps(
        current,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ) + "\n"

    if snapshot.exists() and snapshot.read_text(encoding="utf-8") != serialized:
        raise ValueError("immutable campaign snapshot changed")

    snapshot.write_text(serialized, encoding="utf-8")
    latest_report.parent.mkdir(parents=True, exist_ok=True)
    latest_report.write_text(serialized, encoding="utf-8")
    return latest_report, snapshot


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5M immutable campaign operations persistence"
    )
    parser.add_argument("--fresh-report", required=True)
    parser.add_argument("--latest", required=True)
    parser.add_argument("--history-dir", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    latest, snapshot = persist_campaign_operations(
        fresh_report=Path(args.fresh_report),
        latest_report=Path(args.latest),
        history_dir=Path(args.history_dir),
    )
    print(latest)
    print(snapshot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
