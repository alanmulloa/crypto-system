from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from app.evaluation.experiment_registry import ExperimentRegistry
from app.evaluation.prospective_bootstrap import (
    DEFAULT_MIN_MATURED_OBSERVATIONS,
    build_generic_protocol,
    protocol_to_dict,
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5H.10 generic prospective bootstrap"
    )
    parser.add_argument("--registry", default="research/experiment-registry.json")
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--freeze-manifest", required=True)
    parser.add_argument(
        "--min-matured-observations",
        type=int,
        default=DEFAULT_MIN_MATURED_OBSERVATIONS,
    )
    parser.add_argument(
        "--output",
        default="reports/prospective/bootstrap.json",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    registry = ExperimentRegistry.load(Path(args.registry))
    try:
        experiment = registry.get(args.experiment_id)
    except KeyError as exc:
        raise SystemExit(f"unknown experiment id: {args.experiment_id}") from exc

    manifest = json.loads(Path(args.freeze_manifest).read_text(encoding="utf-8"))
    try:
        protocol = build_generic_protocol(
            experiment=experiment,
            freeze_manifest=manifest,
            min_matured_observations=args.min_matured_observations,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    result = {
        "metadata": {
            "phase": "5H.10",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "research_only": True,
            "phase6_blocked": True,
            "execution_enabled": False,
            "testnet_enabled": False,
            "automatic_promotion": False,
        },
        "protocol": protocol_to_dict(protocol),
        "collection_contract": {
            "signal_rule": (
                "only signal_timestamp_ms strictly greater than frozen_at_ms"
            ),
            "pre_freeze_data": "indicator lookback only; never an outcome",
            "cohorts": ["baseline", "candidate"],
            "immutable_history": True,
        },
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(f"{experiment.id} | GENERIC_PROSPECTIVE_BOOTSTRAP_READY")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
