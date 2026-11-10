from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from app.evaluation.entry_quality import MeanReversionEntryDiagnostics
from app.evaluation.evidence import DEFAULT_EVIDENCE_SYMBOLS, RealEvidenceRunner


WARNINGS = (
    "All entry features are derived from information available at signal time.",
    "Future candles are labels only and are never used as entry features.",
    "Only calibration and validation buckets are eligible for candidate selection.",
    "The previously observed out-of-sample segment is descriptive only.",
    "No bucket automatically changes strategy rules or authorizes execution.",
    "Any Phase 5G variant requires genuinely unseen future or prospective evidence.",
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5F.1 Mean Reversion entry-quality diagnostics"
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=list(DEFAULT_EVIDENCE_SYMBOLS),
    )
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--max-points", type=int, default=8000)
    parser.add_argument("--outcome-hours", type=int, default=24)
    parser.add_argument("--min-bucket-observations", type=int, default=20)
    parser.add_argument(
        "--observation-examples",
        type=int,
        default=25,
        help="observations retained per symbol/segment; summaries always use all data",
    )
    parser.add_argument("--include-all-observations", action="store_true")
    parser.add_argument("--output", default=None)
    return parser.parse_args()


def _compact(payload: dict, *, limit: int | None) -> None:
    for container in [*payload.get("results", []), payload.get("pooled", {})]:
        for segment in container.get("segments", []):
            observations = segment.get("observations", [])
            segment["observation_count"] = len(observations)
            if limit is not None:
                segment["observations"] = observations[:limit]


def main() -> int:
    args = _parse_args()
    if args.days < 90:
        raise SystemExit("--days must be at least 90")
    if args.max_points < 60:
        raise SystemExit("--max-points must be at least 60")
    if args.outcome_hours <= 0:
        raise SystemExit("--outcome-hours must be positive")
    if args.min_bucket_observations <= 0:
        raise SystemExit("--min-bucket-observations must be positive")
    if args.observation_examples < 0:
        raise SystemExit("--observation-examples cannot be negative")

    symbols = tuple(dict.fromkeys(symbol.upper() for symbol in args.symbols))
    evidence = RealEvidenceRunner()
    analyzer = MeanReversionEntryDiagnostics(
        outcome_hours=args.outcome_hours,
        min_bucket_observations=args.min_bucket_observations,
    )
    end_time_ms = evidence.client.now_ms()
    start_time_ms = end_time_ms - args.days * 24 * 60 * 60 * 1000

    results = []
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
        results.append(
            analyzer.run_symbol(
                strategy="mean_reversion",
                points=points,
                candles_by_interval=history,
            )
        )

    pooled = analyzer.pool(results, strategy="mean_reversion")
    payload = {
        "metadata": {
            "phase": "5F.1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "days_requested": args.days,
            "max_points": args.max_points,
            "outcome_hours": args.outcome_hours,
            "min_bucket_observations": args.min_bucket_observations,
            "research_only": True,
            "oos_already_observed": True,
        },
        "methodological_warnings": WARNINGS,
        "results": [asdict(result) for result in results],
        "pooled": asdict(pooled),
    }
    _compact(
        payload,
        limit=None if args.include_all_observations else args.observation_examples,
    )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = args.output or f"reports/phase5f1-mean-reversion-{stamp}.json"
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
