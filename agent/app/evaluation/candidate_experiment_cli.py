from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from app.evaluation.candidate_experiment import MeanReversionCandidateExperiment
from app.evaluation.entry_quality import MeanReversionEntryDiagnostics
from app.evaluation.evidence import RealEvidenceRunner


DEFAULT_SYMBOLS = ("XRPUSDT", "ETHUSDT")

WARNINGS = (
    "Phase 5F.2 is research only and does not alter strategy rules.",
    "Candidates were predetermined from the Phase 5F.1 review.",
    "Only calibration and validation can determine candidate eligibility.",
    "The previously observed out-of-sample segment is descriptive only.",
    "Eligibility only permits a future prospective test; it does not authorize Testnet.",
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5F.2 Mean Reversion candidate experiment"
    )
    parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_SYMBOLS))
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--max-points", type=int, default=8000)
    parser.add_argument("--outcome-hours", type=int, default=24)
    parser.add_argument("--min-observations", type=int, default=20)
    parser.add_argument("--output", default=None)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.days < 90:
        raise SystemExit("--days must be at least 90")
    if args.max_points < 60:
        raise SystemExit("--max-points must be at least 60")
    if args.outcome_hours <= 0:
        raise SystemExit("--outcome-hours must be positive")
    if args.min_observations <= 0:
        raise SystemExit("--min-observations must be positive")

    symbols = tuple(dict.fromkeys(symbol.upper() for symbol in args.symbols))
    evidence = RealEvidenceRunner()
    entry = MeanReversionEntryDiagnostics(
        outcome_hours=args.outcome_hours,
        min_bucket_observations=args.min_observations,
    )
    experiment = MeanReversionCandidateExperiment(
        min_observations=args.min_observations
    )

    end_time_ms = evidence.client.now_ms()
    start_time_ms = end_time_ms - args.days * 24 * 60 * 60 * 1000
    entry_reports = []

    for symbol in symbols:
        history = evidence.fetch_symbol_history(
            symbol=symbol,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
        )
        quote_asset = "USDT" if symbol.endswith("USDT") else ""
        base_asset = symbol[: -len(quote_asset)] if quote_asset else symbol
        points = evidence.historical_runner.run(
            symbol=symbol,
            base_asset=base_asset,
            quote_asset=quote_asset,
            candles_by_interval=history,
            anchor_interval="1h",
            max_points=args.max_points,
        )
        entry_reports.append(
            entry.run_symbol(
                strategy="mean_reversion",
                points=points,
                candles_by_interval=history,
            )
        )

    results = experiment.run_defaults(entry_reports)
    payload = {
        "metadata": {
            "phase": "5F.2",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "days_requested": args.days,
            "max_points": args.max_points,
            "outcome_hours": args.outcome_hours,
            "min_observations": args.min_observations,
            "research_only": True,
            "oos_already_observed": True,
        },
        "methodological_warnings": WARNINGS,
        "results": [asdict(result) for result in results],
    }

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = args.output or f"reports/phase5f2-entry-candidates-{stamp}.json"
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
