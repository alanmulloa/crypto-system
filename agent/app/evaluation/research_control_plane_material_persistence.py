from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _stamp(payload: Mapping[str, Any]) -> str:
    generated_at = str(payload.get("generated_at") or "")
    if not generated_at:
        raise ValueError("generated_at is required")
    return generated_at.replace(":", "-").replace("+", "_")


def persist_material_control_plane(
    *,
    current: Path,
    diff: Path,
    latest: Path,
    history_dir: Path,
    events_dir: Path,
) -> dict[str, Any]:
    snapshot = _load(current)
    change = _load(diff)
    if snapshot.get("phase") != "5V-5Z":
        raise ValueError("invalid control plane phase")
    if snapshot.get("phase6_blocked") is not True:
        raise ValueError("Phase 6 must remain blocked")
    if change.get("phase") != "5Y":
        raise ValueError("invalid control plane diff phase")

    if change.get("changed") is not True:
        return {
            "persisted": False,
            "reason": "NO_MATERIAL_CHANGE",
            "snapshot_sha256": snapshot.get("snapshot_sha256"),
        }

    serialized = json.dumps(snapshot, indent=2, sort_keys=True) + "\n"
    stamp = _stamp(snapshot)
    history_dir.mkdir(parents=True, exist_ok=True)
    events_dir.mkdir(parents=True, exist_ok=True)

    history_path = history_dir / f"{stamp}.json"
    event_path = events_dir / f"{stamp}.json"
    if history_path.exists() and history_path.read_text(encoding="utf-8") != serialized:
        raise ValueError("immutable control-plane history collision")

    event_payload = {
        "phase": "5AB",
        "generated_at": snapshot.get("generated_at"),
        "reason": change.get("reason"),
        "previous_snapshot_sha256": change.get("previous_snapshot_sha256"),
        "current_snapshot_sha256": change.get("current_snapshot_sha256"),
        "state": snapshot.get("state"),
        "blocker_ids": [item.get("id") for item in snapshot.get("blockers", [])],
        "human_action_ids": [
            item.get("id") for item in snapshot.get("human_action_inbox", [])
        ],
        "phase6_blocked": True,
    }
    event_serialized = json.dumps(event_payload, indent=2, sort_keys=True) + "\n"
    if event_path.exists() and event_path.read_text(encoding="utf-8") != event_serialized:
        raise ValueError("immutable control-plane event collision")

    history_path.write_text(serialized, encoding="utf-8")
    event_path.write_text(event_serialized, encoding="utf-8")
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(serialized, encoding="utf-8")
    return {
        "persisted": True,
        "reason": change.get("reason"),
        "history": str(history_path),
        "event": str(event_path),
        "latest": str(latest),
        "snapshot_sha256": snapshot.get("snapshot_sha256"),
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5AA-5AB durable material control-plane persistence"
    )
    parser.add_argument("--current", required=True)
    parser.add_argument("--diff", required=True)
    parser.add_argument("--latest", required=True)
    parser.add_argument("--history-dir", required=True)
    parser.add_argument("--events-dir", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    result = persist_material_control_plane(
        current=Path(args.current),
        diff=Path(args.diff),
        latest=Path(args.latest),
        history_dir=Path(args.history_dir),
        events_dir=Path(args.events_dir),
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
