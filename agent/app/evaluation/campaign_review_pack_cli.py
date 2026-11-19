from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from app.evaluation.campaign_review_pack import build_campaign_review_pack


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5P human campaign review pack"
    )
    parser.add_argument("--operations", required=True)
    parser.add_argument("--incidents", required=True)
    parser.add_argument("--recovery", required=True)
    parser.add_argument("--reproducibility", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    payload = build_campaign_review_pack(
        operations=_load(args.operations),
        incidents=_load(args.incidents),
        recovery=_load(args.recovery),
        reproducibility=_load(args.reproducibility),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"{payload['campaign_id']} | {payload['state']}")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
