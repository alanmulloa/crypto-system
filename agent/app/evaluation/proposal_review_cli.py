from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from app.evaluation.experiment_registry import ExperimentRegistry
from app.evaluation.proposal_review import (
    MIN_VALIDATION_UPLIFT_PCT_POINTS,
    review_discovery_payload,
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5H.5 proposal review gate"
    )
    parser.add_argument("--input", required=True)
    parser.add_argument(
        "--registry",
        default="research/experiment-registry.json",
    )
    parser.add_argument(
        "--output",
        default="reports/phase5h5-proposal-review.json",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    source = Path(args.input)
    registry_path = Path(args.registry)
    payload = json.loads(source.read_text(encoding="utf-8"))
    registry = ExperimentRegistry.load(registry_path)

    reviews = review_discovery_payload(payload, registry)
    counts: dict[str, int] = {}
    for item in reviews:
        counts[item.decision] = counts.get(item.decision, 0) + 1

    result = {
        "metadata": {
            "phase": "5H.5",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_artifact": str(source),
            "registry": str(registry_path),
            "research_only": True,
            "auto_register": False,
            "auto_freeze": False,
            "phase6_blocked": True,
            "min_validation_uplift_pct_points": (
                MIN_VALIDATION_UPLIFT_PCT_POINTS
            ),
        },
        "decision_counts": counts,
        "reviews": [asdict(item) for item in reviews],
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    for item in reviews:
        print(f"{item.proposal_id} | {item.decision}")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
