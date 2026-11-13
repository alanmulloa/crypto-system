from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from app.evaluation.experiment_registry import ExperimentRegistry
from app.evaluation.freeze_review import review_freeze_readiness


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5H.8 freeze review protocol"
    )
    parser.add_argument("--registry", default="research/experiment-registry.json")
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--calibration-artifact", required=True)
    parser.add_argument("--validation-artifact", required=True)
    parser.add_argument("--output", default="reports/phase5h8-freeze-review.json")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    registry_path = Path(args.registry)
    calibration_path = Path(args.calibration_artifact)
    validation_path = Path(args.validation_artifact)

    registry = ExperimentRegistry.load(registry_path)
    try:
        experiment = registry.get(args.experiment_id)
    except KeyError as exc:
        raise SystemExit(f"unknown experiment id: {args.experiment_id}") from exc

    calibration = json.loads(calibration_path.read_text(encoding="utf-8"))
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    review = review_freeze_readiness(
        experiment=experiment,
        calibration_artifact=calibration,
        validation_artifact=validation,
    )

    result = {
        "metadata": {
            "phase": "5H.8",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "registry": str(registry_path),
            "experiment_id": experiment.id,
            "calibration_artifact": str(calibration_path),
            "validation_artifact": str(validation_path),
            "research_only": True,
            "auto_transition": False,
            "auto_freeze": False,
            "phase6_blocked": True,
        },
        "review": asdict(review),
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(f"{experiment.id} | {review.decision}")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
