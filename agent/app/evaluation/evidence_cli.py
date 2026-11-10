from __future__ import annotations

import argparse
from datetime import datetime, timezone

from app.evaluation.evidence import (
    DEFAULT_EVIDENCE_SYMBOLS,
    RealEvidenceRunner,
    write_evidence_json,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Phase 5D real historical evidence using Binance public klines"
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=list(DEFAULT_EVIDENCE_SYMBOLS),
        help="Spot symbols, e.g. BTCUSDT ETHUSDT",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=730,
        help="historical days to fetch; minimum 90",
    )
    parser.add_argument(
        "--max-points",
        type=int,
        default=8000,
        help="maximum recent hourly evaluation points per symbol",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="JSON report path; defaults to reports/evidence-<UTC timestamp>.json",
    )
    args = parser.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = args.output or f"reports/evidence-{stamp}.json"
    report = RealEvidenceRunner().run(
        symbols=args.symbols,
        days=args.days,
        max_points=max(60, args.max_points),
    )
    path = write_evidence_json(report, output)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
