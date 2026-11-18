from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from app.evaluation.generic_prospective_runner import run_generic_prospective
from app.evaluation.historical import HistoricalSanityRunner
from app.evaluation.prospective_bootstrap import protocol_from_bootstrap
from app.market.binance_public import BinancePublicClient


DAY_MS = 24 * 60 * 60 * 1000


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5H.13 public-data generic prospective runner"
    )
    parser.add_argument("--bootstrap", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--as-of-ms", type=int)
    parser.add_argument("--lookback-days", type=int, default=300)
    return parser.parse_args(argv)


def build_public_report(
    *,
    bootstrap_payload: dict,
    as_of_ms: int | None = None,
    lookback_days: int = 300,
    client: BinancePublicClient | None = None,
) -> dict:
    if lookback_days < 90:
        raise ValueError("lookback_days must be at least 90")
    protocol = protocol_from_bootstrap(bootstrap_payload)
    market = client or BinancePublicClient()
    effective_as_of = as_of_ms or market.now_ms()
    start = max(0, protocol.frozen_at_ms - lookback_days * DAY_MS)
    intervals = ("15m", "1h", "4h", "1d")
    candles = {
        interval: market.historical_klines(
            protocol.symbol,
            interval,
            start_time_ms=start,
            end_time_ms=effective_as_of,
        )
        for interval in intervals
    }

    info = next(
        (
            item
            for item in market.exchange_info()
            if item.symbol == protocol.symbol
        ),
        None,
    )
    if info is None or not info.spot_allowed:
        raise ValueError("frozen symbol is not available for Spot research")

    points = HistoricalSanityRunner().run(
        symbol=info.symbol,
        base_asset=info.base_asset,
        quote_asset=info.quote_asset,
        candles_by_interval=candles,
    )
    return run_generic_prospective(
        protocol=protocol,
        points=points,
        candles_by_interval=candles,
        as_of_ms=effective_as_of,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    bootstrap = json.loads(Path(args.bootstrap).read_text(encoding="utf-8"))
    try:
        report = build_public_report(
            bootstrap_payload=bootstrap,
            as_of_ms=args.as_of_ms,
            lookback_days=args.lookback_days,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
