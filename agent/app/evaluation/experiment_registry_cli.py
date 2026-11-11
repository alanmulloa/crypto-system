from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from app.evaluation.experiment_registry import (
    ExperimentRegistry,
    ExperimentStatus,
    ResearchExperiment,
)


DEFAULT_REGISTRY = Path("research/experiment-registry.json")
SUPPORTED_OPERATORS = ("<=", ">=", "==", "<", ">")


def _threshold(value: str) -> float | str:
    try:
        return float(value)
    except ValueError:
        if not value.strip():
            raise argparse.ArgumentTypeError("threshold cannot be empty")
        return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Phase 5H research experiment registry"
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

    register = subparsers.add_parser(
        "register",
        help="register a new experiment as DRAFT",
    )
    register.add_argument("--id", required=True)
    register.add_argument("--symbol", required=True)
    register.add_argument("--strategy", required=True)
    register.add_argument("--direction", required=True)
    register.add_argument("--feature", required=True)
    register.add_argument("--operator", choices=SUPPORTED_OPERATORS, required=True)
    register.add_argument("--threshold", type=_threshold, required=True)
    register.add_argument("--outcome-hours", type=int, required=True)
    register.add_argument("--fee-bps", type=float, required=True)
    register.add_argument("--slippage-bps", type=float, required=True)
    register.add_argument("--artifact-path", required=True)
    register.add_argument("--calibration-period", default=None)
    register.add_argument("--validation-period", default=None)

    transition = subparsers.add_parser(
        "transition",
        help="transition an existing experiment to the next allowed status",
    )
    transition.add_argument("experiment_id")
    transition.add_argument(
        "status",
        choices=[status.value for status in ExperimentStatus],
    )
    transition.add_argument("--decision", default=None)
    transition.add_argument("--freeze-at-ms", type=int, default=None)

    return parser


def _save(path: Path, registry: ExperimentRegistry) -> None:
    registry.save(path)


def _register(args: argparse.Namespace, path: Path, registry: ExperimentRegistry) -> int:
    experiment = ResearchExperiment(
        id=args.id,
        symbol=args.symbol.upper(),
        strategy=args.strategy,
        direction=args.direction.upper(),
        feature=args.feature,
        operator=args.operator,
        threshold=args.threshold,
        calibration_period=args.calibration_period,
        validation_period=args.validation_period,
        freeze_at_ms=None,
        outcome_hours=args.outcome_hours,
        fee_bps=args.fee_bps,
        slippage_bps=args.slippage_bps,
        status=ExperimentStatus.DRAFT,
        decision=None,
        artifact_path=args.artifact_path,
    )
    try:
        updated = registry.add_experiment(experiment)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    _save(path, updated)
    print(f"REGISTERED | {experiment.id} | DRAFT")
    return 0


def _transition(
    args: argparse.Namespace,
    path: Path,
    registry: ExperimentRegistry,
) -> int:
    try:
        current = registry.get(args.experiment_id)
    except KeyError as exc:
        raise SystemExit(f"unknown experiment id: {args.experiment_id}") from exc

    new_status = ExperimentStatus(args.status)
    changes = {}
    if new_status is ExperimentStatus.FROZEN:
        if args.freeze_at_ms is None:
            raise SystemExit("--freeze-at-ms is required when transitioning to FROZEN")
        changes["freeze_at_ms"] = args.freeze_at_ms
    elif args.freeze_at_ms is not None:
        raise SystemExit("--freeze-at-ms is only valid when transitioning to FROZEN")

    try:
        transitioned = current.transition(
            new_status,
            decision=args.decision,
            **changes,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    updated = registry.replace_experiment(transitioned)
    _save(path, updated)
    print(
        f"TRANSITIONED | {transitioned.id} | "
        f"{current.status.value} -> {transitioned.status.value}"
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    path = Path(args.registry)
    registry = ExperimentRegistry.load(path)

    if args.command == "register":
        return _register(args, path, registry)
    if args.command == "transition":
        return _transition(args, path, registry)

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
