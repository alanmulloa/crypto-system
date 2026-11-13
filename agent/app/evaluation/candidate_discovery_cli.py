from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from app.evaluation.candidate_discovery import discover_from_phase5f1_payload


WARNINGS = (
    "Phase 5H.4 is research-only and does not register candidates automatically.",
    "Only pre-defined Phase 5F.1 buckets that map to simple rules are eligible.",
    "Only calibration + validation evidence is used for discovery.",
    "Previously observed out-of-sample evidence is not used for candidate selection.",
    "No proposal changes strategy rules, freezes an experiment, or authorizes Phase 6.",
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5H.4 research-only candidate discovery"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Phase 5F.1 JSON artifact",
    )
    parser.add_argument(
        "--output",
        default="reports/phase5h4-candidate-discovery.json",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    source = Path(args.input)
    payload = json.loads(source.read_text(encoding="utf-8"))
    proposals = discover_from_phase5f1_payload(payload)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "metadata": {
            "phase": "5H.4",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_artifact": str(source),
            "research_only": True,
            "auto_register": False,
            "auto_freeze": False,
            "phase6_blocked": True,
        },
        "methodological_warnings": WARNINGS,
        "proposal_count": len(proposals),
        "proposals": [asdict(item) for item in proposals],
    }
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(f"{len(proposals)} proposals")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
