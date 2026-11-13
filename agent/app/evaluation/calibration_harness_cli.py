from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from app.evaluation.calibration_harness import (
    MIN_CALIBRATION_OBSERVATIONS,
    run_calibration_review,
)
from app.evaluation.experiment_registry import (
    ExperimentRegistry,
    experiment_definition_snapshot,
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5H.6 calibration harness"
    )
    parser.add_argument("--input", required=True, help="Phase 5F.1 JSON artifact")
    parser.add_argument(
        "--registry",
        default="research/experiment-registry.json",
    )
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument(
        "--output",
        default="reports/phase5h6-calibration.json",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    source = Path(args.input)
    registry_path = Path(args.registry)

    payload = json.loads(source.read_text(encoding="utf-8"))
    registry = ExperimentRegistry.load(registry_path)
    try:
        experiment = registry.get(args.experiment_id)
    except KeyError as exc:
        raise SystemExit(f"unknown experiment id: {args.experiment_id}") from exc

    try:
        review = run_calibration_review(
            experiment=experiment,
            phase5f1_payload=payload,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    result = {
        "metadata": {
            "phase": "5H.6",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_artifact": str(source),
            "registry": str(registry_path),
            "experiment_id": experiment.id,
            "segment_used": "calibration",
            "validation_read": False,
            "oos_read": False,
            "research_only": True,
            "auto_transition": False,
            "phase6_blocked": True,
            "min_calibration_observations": MIN_CALIBRATION_OBSERVATIONS,
        },
        "experiment_definition": experiment_definition_snapshot(experiment),
        "review": asdict(review),
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    print(
        f"{review.experiment_id} | {review.decision} | "
        f"observations={review.observations}"
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
