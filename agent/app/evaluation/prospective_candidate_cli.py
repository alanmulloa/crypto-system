from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from app.evaluation.evidence import RealEvidenceRunner
from app.evaluation.prospective_candidate import (
    DEFAULT_FREEZE_AT_ISO,
    ProspectiveXrpCandidateEvaluator,
    parse_iso_ms,
)


LOOKBACK_DAYS = 90


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5G prospective XRP candidate evidence harness"
    )
    parser.add_argument("--freeze-at", default=DEFAULT_FREEZE_AT_ISO)
    parser.add_argument("--outcome-hours", type=int, default=24)
    parser.add_argument("--min-matured-observations", type=int, default=20)
    parser.add_argument("--output", default="reports/phase5g-xrp-prospective.json")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.outcome_hours <= 0:
        raise SystemExit("--outcome-hours must be positive")
    if args.min_matured_observations <= 0:
        raise SystemExit("--min-matured-observations must be positive")

    freeze_at_ms = parse_iso_ms(args.freeze_at)
    evidence = RealEvidenceRunner()
    as_of_ms = evidence.client.now_ms()
    if as_of_ms <= freeze_at_ms:
        raise SystemExit("current Binance time is not after the frozen cutoff")

    start_time_ms = freeze_at_ms - LOOKBACK_DAYS * 24 * 60 * 60 * 1000
    history = evidence.fetch_symbol_history(
        symbol="XRPUSDT",
        start_time_ms=start_time_ms,
        end_time_ms=as_of_ms,
    )
    points = evidence.historical_runner.run(
        symbol="XRPUSDT",
        base_asset="XRP",
        quote_asset="USDT",
        candles_by_interval=history,
        anchor_interval="1h",
        max_points=None,
    )

    evaluator = ProspectiveXrpCandidateEvaluator(
        frozen_at_ms=freeze_at_ms,
        outcome_hours=args.outcome_hours,
        min_matured_observations=args.min_matured_observations,
    )
    report = evaluator.run(
        points=points,
        candles_by_interval=history,
        as_of_ms=as_of_ms,
    )
    payload = asdict(report)
    payload["metadata"] = {
        "phase": "5G-prospective",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "public_binance_only": True,
        "lookback_days_for_indicators": LOOKBACK_DAYS,
    }

    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
