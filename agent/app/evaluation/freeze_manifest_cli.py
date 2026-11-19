from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from app.evaluation.experiment_registry import ExperimentRegistry
from app.evaluation.freeze_manifest import build_freeze_manifest


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5H.9 freeze manifest generator"
    )
    parser.add_argument("--registry", default="research/experiment-registry.json")
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--calibration-artifact", required=True)
    parser.add_argument("--validation-artifact", required=True)
    parser.add_argument("--freeze-review-artifact", required=True)
    parser.add_argument("--output", default="reports/phase5h9-freeze-manifest.json")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    registry_path = Path(args.registry)
    calibration_path = Path(args.calibration_artifact)
    validation_path = Path(args.validation_artifact)
    freeze_review_path = Path(args.freeze_review_artifact)

    registry = ExperimentRegistry.load(registry_path)
    try:
        experiment = registry.get(args.experiment_id)
    except KeyError as exc:
        raise SystemExit(f"unknown experiment id: {args.experiment_id}") from exc

    calibration = json.loads(calibration_path.read_text(encoding="utf-8"))
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    freeze_review = json.loads(freeze_review_path.read_text(encoding="utf-8"))

    try:
        manifest = build_freeze_manifest(
            experiment=experiment,
            calibration_artifact=calibration,
            validation_artifact=validation,
            freeze_review_artifact=freeze_review,
            calibration_path=str(calibration_path),
            validation_path=str(validation_path),
            freeze_review_path=str(freeze_review_path),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"{experiment.id} | FREEZE_MANIFEST_READY | "
        f"{manifest['definition_fingerprint_sha256']}"
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
