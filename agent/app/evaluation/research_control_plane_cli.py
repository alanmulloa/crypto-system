from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from app.evaluation.experiment_registry import ExperimentRegistry
from app.evaluation.research_control_plane import (
    build_research_control_plane,
    diff_control_plane,
)


def _load(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5V-5Z unified research control plane"
    )
    parser.add_argument(
        "--registry",
        default="research/experiment-registry.json",
    )
    parser.add_argument("--phase5g-root", default="reports/phase5g")
    parser.add_argument(
        "--campaign-governance",
        default="reports/phase5nq/governance.json",
    )
    parser.add_argument(
        "--writer-policy",
        default="reports/phase5t/writer-policy.json",
    )
    parser.add_argument(
        "--phase5m-root",
        default="reports/phase5m",
    )
    parser.add_argument(
        "--dependencies-output",
        default="reports/phase5vz/dependencies.json",
    )
    parser.add_argument(
        "--previous",
        default="reports/phase5vz/latest.json",
    )
    parser.add_argument(
        "--output",
        default="reports/phase5vz/current.json",
    )
    parser.add_argument(
        "--diff-output",
        default="reports/phase5vz/diff.json",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    current = build_research_control_plane(
        registry=ExperimentRegistry.load(Path(args.registry)),
        phase5g_root=Path(args.phase5g_root),
        campaign_governance_path=Path(args.campaign_governance),
        writer_policy_path=Path(args.writer_policy),
        phase5m_root=Path(args.phase5m_root),
        generated_at=datetime.now(timezone.utc),
    )
    dependencies_output = Path(args.dependencies_output)
    dependencies_output.parent.mkdir(parents=True, exist_ok=True)
    dependencies_output.write_text(
        json.dumps(
            current["dependencies"],
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    previous = _load(Path(args.previous))
    diff = diff_control_plane(previous, current)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(current, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    diff_output = Path(args.diff_output)
    diff_output.parent.mkdir(parents=True, exist_ok=True)
    diff_output.write_text(
        json.dumps(diff, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"state={current['state']} "
        f"human_actions={len(current['human_action_inbox'])} "
        f"blockers={len(current['blockers'])}"
    )
    print(output)
    print(diff_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
