from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence


def persist_control_plane(
    *,
    current: Path,
    latest: Path,
) -> Path:
    payload = json.loads(current.read_text(encoding="utf-8"))
    if payload.get("phase") != "5V-5Z":
        raise ValueError("invalid control plane phase")
    if payload.get("phase6_blocked") is not True:
        raise ValueError("Phase 6 must remain blocked")
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return latest


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Persist Phase 5V-5Z latest control plane snapshot"
    )
    parser.add_argument("--current", required=True)
    parser.add_argument("--latest", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    path = persist_control_plane(
        current=Path(args.current),
        latest=Path(args.latest),
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
