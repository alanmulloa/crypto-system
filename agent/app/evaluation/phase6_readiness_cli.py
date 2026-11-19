from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from app.config import Settings
from app.evaluation.phase6_approval import (
    HumanApproval,
    build_pending_approval,
)
from app.evaluation.phase6_execution_boundary import build_execution_boundary
from app.evaluation.phase6_readiness import (
    build_phase6_readiness,
    readiness_to_dict,
)
from app.evaluation.phase6_research_gate import build_research_gate_snapshot
from app.evaluation.phase6_risk_preflight import build_risk_preflight
from app.evaluation.phase6_testnet_dry_run import (
    build_testnet_dry_run_plan,
    dry_run_plan_to_dict,
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5J Phase 6 readiness review"
    )
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--decision", required=True)
    parser.add_argument("--review", required=True)
    parser.add_argument("--approval")
    parser.add_argument("--output", default="reports/phase6-readiness.json")
    return parser.parse_args(argv)


def _load_approval(path: str | None, experiment_id: str) -> HumanApproval:
    if path is None:
        return build_pending_approval(experiment_id)
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return HumanApproval(**payload)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    decision = json.loads(Path(args.decision).read_text(encoding="utf-8"))
    review = json.loads(Path(args.review).read_text(encoding="utf-8"))
    settings = Settings()

    research = build_research_gate_snapshot(
        experiment_id=args.experiment_id,
        decision=decision,
        review=review,
    )
    risk = build_risk_preflight(settings)
    boundary = build_execution_boundary()
    approval = _load_approval(args.approval, args.experiment_id)
    readiness = build_phase6_readiness(
        research=research,
        risk=risk,
        boundary=boundary,
        approval=approval,
    )
    dry_run = build_testnet_dry_run_plan(
        readiness=readiness,
        settings=settings,
    )

    payload = {
        "phase": "5J",
        "experiment_id": args.experiment_id,
        "research": research.__dict__,
        "risk": risk.__dict__,
        "execution_boundary": boundary.__dict__,
        "approval": approval.__dict__,
        "readiness": readiness_to_dict(readiness),
        "dry_run_plan": dry_run_plan_to_dict(dry_run),
        "phase6_eligible": False,
        "phase6_blocked": True,
        "automatic_activation": False,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(f"{args.experiment_id} | {readiness.state}")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
