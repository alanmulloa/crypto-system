from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from app.evaluation.experiment_registry import ExperimentRegistry
from app.evaluation.research_campaign import (
    ResearchCampaign,
    campaign_status_payload,
)
from app.evaluation.research_campaign_runner import run_campaign_screen
from app.evaluation.research_portfolio import (
    build_promotion_queue,
    queue_to_dict,
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5K parallel research campaign"
    )
    parser.add_argument("--campaign", required=True)
    parser.add_argument(
        "--registry",
        default="research/experiment-registry.json",
    )
    parser.add_argument("--status-output", required=True)
    parser.add_argument("--screen-output")
    parser.add_argument("--queue-output")
    parser.add_argument("--as-of-ms", type=int)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    campaign = ResearchCampaign.from_dict(
        json.loads(Path(args.campaign).read_text(encoding="utf-8"))
    )
    as_of_ms = args.as_of_ms or int(
        datetime.now(timezone.utc).timestamp() * 1000
    )
    status = campaign_status_payload(campaign, as_of_ms=as_of_ms)
    status_path = Path(args.status_output)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(
        json.dumps(status, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"{campaign.id} | {status['state']}")

    if not status["screening_allowed"]:
        print(status_path)
        return 0

    if not args.screen_output or not args.queue_output:
        raise SystemExit(
            "--screen-output and --queue-output are required when screening is ready"
        )

    screen = run_campaign_screen(
        campaign=campaign,
        as_of_ms=as_of_ms,
    )
    screen_path = Path(args.screen_output)
    screen_path.parent.mkdir(parents=True, exist_ok=True)
    screen_path.write_text(
        json.dumps(screen, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    registry = ExperimentRegistry.load(Path(args.registry))
    queue = build_promotion_queue(
        proposals=screen["proposals"],
        registry=registry,
    )
    queue_payload = queue_to_dict(queue)
    queue_path = Path(args.queue_output)
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(
        json.dumps(queue_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(screen_path)
    print(queue_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
