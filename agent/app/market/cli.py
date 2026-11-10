from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from app.market.binance_public import BinancePublicClient
from app.market.scanner import MarketScanner, ScannerConfig


def _json_default(value):
    return getattr(value, "value", str(value))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 1 public Binance market scanner")
    parser.add_argument("--limit", type=int, default=10, help="maximum candidates to print")
    parser.add_argument("--prefilter", type=int, default=30, help="liquid symbols to analyze")
    parser.add_argument("--min-volume", type=float, default=5_000_000, help="minimum 24h quote volume")
    parser.add_argument("--min-trades", type=int, default=1_000, help="minimum 24h trade count")
    args = parser.parse_args()

    scanner = MarketScanner(
        BinancePublicClient(),
        ScannerConfig(
            candidate_limit=max(1, args.limit),
            prefilter_limit=max(1, args.prefilter),
            min_quote_volume_24h=max(0.0, args.min_volume),
            min_trade_count_24h=max(0, args.min_trades),
        ),
    )
    candidates = scanner.scan()
    print(json.dumps([asdict(item) for item in candidates], indent=2, default=_json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
