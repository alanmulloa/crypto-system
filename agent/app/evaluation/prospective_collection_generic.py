from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from app.evaluation.prospective_bootstrap import (
    GenericProspectiveProtocol,
    assert_generic_history_compatible,
    validate_generic_report,
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def protocol_from_bootstrap(payload: Mapping[str, Any]) -> GenericProspectiveProtocol:
    metadata = payload.get("metadata") or {}
    if metadata.get("phase") != "5H.10":
        raise ValueError("bootstrap artifact must be Phase 5H.10")
    if metadata.get("research_only") is not True:
        raise ValueError("bootstrap must be research_only")
    if metadata.get("phase6_blocked") is not True:
        raise ValueError("bootstrap must keep phase6_blocked=true")
    return GenericProspectiveProtocol(**dict(payload["protocol"]))


def _snapshot_name(report: Mapping[str, Any]) -> str:
    created_at = str((report.get("metadata") or {}).get("created_at") or "")
    if not created_at:
        raise ValueError("metadata.created_at is required")
    safe = created_at.replace(":", "-").replace("+", "_")
    return f"{safe}.json"


def collect_generic_report(
    *,
    fresh_report: Path,
    bootstrap_artifact: Path,
    latest_report: Path,
    history_dir: Path,
) -> tuple[Path, Path]:
    bootstrap = _load(bootstrap_artifact)
    protocol = protocol_from_bootstrap(bootstrap)
    current = _load(fresh_report)
    validate_generic_report(current, protocol=protocol)

    if latest_report.exists():
        previous = _load(latest_report)
        assert_generic_history_compatible(
            previous,
            current,
            protocol=protocol,
        )

    history_dir.mkdir(parents=True, exist_ok=True)
    snapshot = history_dir / _snapshot_name(current)
    serialized = json.dumps(
        current,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ) + "\n"

    if snapshot.exists() and snapshot.read_text(encoding="utf-8") != serialized:
        raise ValueError(
            f"immutable snapshot already exists with different content: {snapshot}"
        )

    snapshot.write_text(serialized, encoding="utf-8")
    latest_report.parent.mkdir(parents=True, exist_ok=True)
    latest_report.write_text(serialized, encoding="utf-8")
    return latest_report, snapshot


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5H.10 generic prospective persistence gate"
    )
    parser.add_argument("--fresh-report", required=True)
    parser.add_argument("--bootstrap", required=True)
    parser.add_argument("--latest", required=True)
    parser.add_argument("--history-dir", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    latest, snapshot = collect_generic_report(
        fresh_report=Path(args.fresh_report),
        bootstrap_artifact=Path(args.bootstrap),
        latest_report=Path(args.latest),
        history_dir=Path(args.history_dir),
    )
    print(latest)
    print(snapshot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
