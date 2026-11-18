from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from app.evaluation.experiment_registry import ExperimentRegistry
from app.evaluation.research_experiment_planner import plan_to_dict


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5H.14 multi-experiment research planner"
    )
    parser.add_argument("--registry", default="research/experiment-registry.json")
    parser.add_argument("--output", default="reports/research-plan.json")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    registry = ExperimentRegistry.load(Path(args.registry))
    payload = plan_to_dict(registry)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    for item in payload["experiments"]:
        print(
            f"{item['experiment_id']} | {item['status']} | "
            f"{item['next_action']}"
        )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
