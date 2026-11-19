from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from app.evaluation.experiment_registry import ExperimentRegistry
from app.evaluation.research_ops import build_research_ops_report


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5I research operations report"
    )
    parser.add_argument("--registry", default="research/experiment-registry.json")
    parser.add_argument("--phase5g-root", default="reports/phase5g")
    parser.add_argument("--generic-root", default="reports/prospective")
    parser.add_argument("--max-age-hours", type=float, default=12.0)
    parser.add_argument("--output", default="reports/research-ops.json")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    registry = ExperimentRegistry.load(Path(args.registry))
    report = build_research_ops_report(
        registry=registry,
        phase5g_root=Path(args.phase5g_root),
        generic_root=Path(args.generic_root),
        as_of=datetime.now(timezone.utc),
        max_age_hours=args.max_age_hours,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    for item in report["experiments"]:
        state = item.get("state", item.get("health_state"))
        print(
            f"{item['experiment_id']} | {state} | "
            f"{item['recommended_action']}"
        )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
