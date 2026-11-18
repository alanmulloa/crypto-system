from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from app.evaluation.experiment_registry import ExperimentRegistry
from app.evaluation.research_lineage_audit import build_lineage_audit


_FILES = {
    "calibration": "calibration.json",
    "validation": "validation.json",
    "freeze_review": "freeze-review.json",
    "manifest": "freeze-manifest.json",
    "bootstrap": "bootstrap.json",
    "latest": "latest.json",
    "review": "review.json",
    "decision": "decision.json",
}


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5H.16 research lineage audit"
    )
    parser.add_argument("--registry", default="research/experiment-registry.json")
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    registry = ExperimentRegistry.load(Path(args.registry))
    try:
        experiment = registry.get(args.experiment_id)
    except KeyError as exc:
        raise SystemExit(f"unknown experiment id: {args.experiment_id}") from exc

    root = Path(args.artifact_root)
    artifacts = {}
    for name, filename in _FILES.items():
        path = root / filename
        if path.exists():
            artifacts[name] = json.loads(path.read_text(encoding="utf-8"))

    audit = build_lineage_audit(
        experiment=experiment,
        artifacts=artifacts,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(audit, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(f"{experiment.id} | {audit['status']}")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
