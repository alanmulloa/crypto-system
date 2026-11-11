from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from app.evaluation.candidate_workspace import (
    CandidateResearchWorkspace,
    initialize_workspace,
)
from app.evaluation.experiment_registry import ExperimentRegistry


DEFAULT_REGISTRY = Path("research/experiment-registry.json")
DEFAULT_WORKSPACE_ROOT = Path("research/workspaces")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Phase 5H.2 candidate research workspace"
    )
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--workspace-root", default=str(DEFAULT_WORKSPACE_ROOT))
    parser.add_argument("--json", action="store_true")

    subparsers = parser.add_subparsers(dest="command", required=True)
    init = subparsers.add_parser("init", help="initialize an eligible workspace")
    init.add_argument("experiment_id")

    validate = subparsers.add_parser(
        "validate",
        help="validate a workspace against the registry",
    )
    validate.add_argument("experiment_id")

    show = subparsers.add_parser("show", help="show workspace metadata")
    show.add_argument("experiment_id")
    return parser


def _manifest_path(root: Path, experiment_id: str) -> Path:
    return root / experiment_id / "workspace.json"


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    registry = ExperimentRegistry.load(Path(args.registry))
    root = Path(args.workspace_root)

    try:
        experiment = registry.get(args.experiment_id)
    except KeyError as exc:
        raise SystemExit(f"unknown experiment id: {args.experiment_id}") from exc

    if args.command == "init":
        try:
            manifest = initialize_workspace(
                experiment=experiment,
                workspace_root=root,
            )
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        print(manifest)
        return 0

    manifest = _manifest_path(root, args.experiment_id)
    if not manifest.exists():
        raise SystemExit(f"workspace does not exist: {manifest}")
    workspace = CandidateResearchWorkspace.load(manifest)

    if args.command == "validate":
        try:
            workspace.validate_against(experiment)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        print(f"VALID | {args.experiment_id} | {experiment.status.value}")
        return 0

    payload = workspace.to_dict()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
    else:
        print(f"experiment_id: {workspace.experiment_id}")
        print(f"workspace_kind: {workspace.workspace_kind}")
        print(f"research_only: {workspace.research_only}")
        print(f"phase6_blocked: {workspace.phase6_blocked}")
        print(f"definition: {json.dumps(dict(workspace.definition), sort_keys=True)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
