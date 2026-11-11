from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from app.evaluation.experiment_registry import ExperimentRegistry


DEFAULT_REGISTRY = Path("research/experiment-registry.json")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Phase 5H.1 research experiment registry inspector"
    )
    parser.add_argument(
        "--registry",
        default=str(DEFAULT_REGISTRY),
        help="registry JSON path (default: research/experiment-registry.json)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list", help="list registered experiments")

    show = subparsers.add_parser("show", help="show one registered experiment")
    show.add_argument("experiment_id")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    registry = ExperimentRegistry.load(Path(args.registry))

    if args.command == "list":
        experiments = sorted(registry.experiments, key=lambda item: item.id)
        if args.json:
            print(
                json.dumps(
                    [item.to_dict() for item in experiments],
                    indent=2,
                    sort_keys=True,
                    allow_nan=False,
                )
            )
        else:
            for item in experiments:
                decision = item.decision or "-"
                print(
                    f"{item.id} | {item.status.value} | {item.symbol} | "
                    f"{item.strategy} {item.direction} | decision={decision}"
                )
        return 0

    try:
        experiment = registry.get(args.experiment_id)
    except KeyError as exc:
        raise SystemExit(f"unknown experiment id: {args.experiment_id}") from exc

    if args.json:
        print(json.dumps(experiment.to_dict(), indent=2, sort_keys=True))
    else:
        for key, value in experiment.to_dict().items():
            print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
