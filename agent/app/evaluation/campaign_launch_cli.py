from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from app.evaluation.campaign_launch import (
    build_campaign_launch_status_from_files,
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5AK-5AO campaign launch verification"
    )
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--seal", required=True)
    parser.add_argument("--operations", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    payload = build_campaign_launch_status_from_files(
        campaign_path=Path(args.campaign),
        seal_path=Path(args.seal),
        operations_path=Path(args.operations),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"{payload['campaign_id']} | {payload['state']} | "
        f"definition_matches={payload['definition_matches_seal']}"
    )
    print(output)
    return 0 if payload["definition_matches_seal"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
