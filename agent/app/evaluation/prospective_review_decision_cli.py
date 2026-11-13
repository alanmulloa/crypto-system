from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from app.evaluation.prospective_bootstrap import protocol_from_bootstrap
from app.evaluation.prospective_decision_generic import build_generic_decision
from app.evaluation.prospective_review_generic import build_generic_review


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5H.11 generic prospective review and decision"
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--bootstrap", required=True)
    parser.add_argument("--review-output", required=True)
    parser.add_argument("--decision-output", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    report = json.loads(Path(args.input).read_text(encoding="utf-8"))
    bootstrap = json.loads(Path(args.bootstrap).read_text(encoding="utf-8"))
    try:
        protocol = protocol_from_bootstrap(bootstrap)
        review = build_generic_review(report, protocol=protocol)
        decision = build_generic_decision(report, protocol=protocol)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    review_output = Path(args.review_output)
    decision_output = Path(args.decision_output)
    review_output.parent.mkdir(parents=True, exist_ok=True)
    decision_output.parent.mkdir(parents=True, exist_ok=True)

    review_output.write_text(
        json.dumps(review, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    decision_output.write_text(
        json.dumps(decision, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    progress = review["progress"]
    print(
        f"{review['state']} | candidate matured "
        f"{progress['matured_candidate_observations']}/"
        f"{progress['required_matured_candidate_observations']}"
    )
    print(
        f"{decision['decision']} | phase6_blocked="
        f"{decision['phase6_blocked']}"
    )
    print(review_output)
    print(decision_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
