from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from app.evaluation.campaign_operations import (
    build_live_campaign_operations,
)
from app.evaluation.experiment_registry import ExperimentRegistry
from app.evaluation.research_campaign import ResearchCampaign


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5L research campaign operations"
    )
    parser.add_argument("--campaign", required=True)
    parser.add_argument(
        "--registry",
        default="research/experiment-registry.json",
    )
    parser.add_argument(
        "--reports-root",
        default="reports/phase5k",
    )
    parser.add_argument(
        "--output",
        default="reports/phase5l/campaign-operations.json",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    campaign = ResearchCampaign.from_dict(
        json.loads(Path(args.campaign).read_text(encoding="utf-8"))
    )
    registry = ExperimentRegistry.load(Path(args.registry))
    report = build_live_campaign_operations(
        campaign=campaign,
        registry=registry,
        reports_root=Path(args.reports_root),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    readiness = report["screening_readiness"]
    progress = report["progress"]
    print(
        f"{campaign.id} | {readiness['state']} | "
        f"{progress['progress_pct']:.2f}%"
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
