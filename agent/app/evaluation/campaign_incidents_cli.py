from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from app.evaluation.campaign_incidents import (
    detect_campaign_incidents,
    incidents_to_dict,
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5M campaign incident detector"
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    report = json.loads(Path(args.input).read_text(encoding="utf-8"))
    payload = incidents_to_dict(detect_campaign_incidents(report))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"incidents={payload['incident_count']}")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
