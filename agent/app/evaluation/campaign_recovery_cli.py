from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from app.evaluation.campaign_recovery import build_recovery_plan


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5N campaign incident recovery planner"
    )
    parser.add_argument("--incidents", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    payload = json.loads(Path(args.incidents).read_text(encoding="utf-8"))
    plan = build_recovery_plan(payload)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"incidents={plan['incident_count']} severity={plan['highest_severity']}")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
