from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from app.evaluation.diagnostics import (
    DiagnosticConfig,
    DiagnosticsReport,
    StrategyDiagnostics,
    interval_quality,
)
from app.evaluation.evidence import (
    DEFAULT_EVIDENCE_SYMBOLS,
    EVIDENCE_INTERVALS,
    RealEvidenceRunner,
)


METHODOLOGICAL_WARNINGS = (
    "The previously observed out-of-sample segment is descriptive only.",
    "Do not select or promote exit parameters using the observed OOS segment.",
    "ATR sensitivity is research-eligible only for calibration/validation rows.",
    "Any selected experimental configuration requires genuinely unseen future data "
    "or prospective evaluation before it can be called validated.",
    "This report is research only and cannot place orders.",
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Phase 5F research-only strategy path diagnostics and exit sensitivity"
        )
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=list(DEFAULT_EVIDENCE_SYMBOLS),
        help="public Binance Spot symbols",
    )
    parser.add_argument(
        "--strategy",
        default="mean_reversion",
        help="strategy to diagnose; default: mean_reversion",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=730,
        help="historical calendar days to request; minimum 90",
    )
    parser.add_argument(
        "--max-points",
        type=int,
        default=8000,
        help="maximum recent hourly historical points per symbol",
    )
    parser.add_argument(
        "--path-examples",
        type=int,
        default=25,
        help="maximum path diagnostics retained per symbol/segment in JSON",
    )
    parser.add_argument(
        "--include-all-paths",
        action="store_true",
        help="retain every individual path diagnostic; can make JSON large",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="JSON path; defaults to reports/phase5f-<strategy>-<UTC>.json",
    )
    return parser.parse_args()


def _compact_paths(payload: dict, *, limit: int | None) -> None:
    for result in payload.get("results", []):
        for segment in result.get("segments", []):
            paths = segment.get("paths", [])
            segment["path_diagnostics_total"] = len(paths)
            if limit is not None:
                segment["paths"] = paths[:limit]


def main() -> int:
    args = _parse_args()
    if args.days < 90:
        raise SystemExit("--days must be at least 90")
    if args.max_points < 60:
        raise SystemExit("--max-points must be at least 60")
    if args.path_examples < 0:
        raise SystemExit("--path-examples cannot be negative")

    symbols = tuple(dict.fromkeys(symbol.upper() for symbol in args.symbols))
    evidence = RealEvidenceRunner()
    diagnostics = StrategyDiagnostics(
        DiagnosticConfig(
            fee_bps=10,
            slippage_bps=5,
            notional_usd=100,
            require_entry_range=True,
        )
    )
    end_time_ms = evidence.client.now_ms()
    start_time_ms = end_time_ms - args.days * 24 * 60 * 60 * 1000

    results = []
    quality = []
    for symbol in symbols:
        history = evidence.fetch_symbol_history(
            symbol=symbol,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
        )
        quality.append(
            (
                symbol,
                tuple(
                    interval_quality(interval, history[interval])
                    for interval in EVIDENCE_INTERVALS
                ),
            )
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
            diagnostics.run_symbol(
                strategy=args.strategy,
                points=points,
                candles_by_interval=history,
            )
        )

    report = DiagnosticsReport(
        strategy=args.strategy,
        symbols=symbols,
        fee_bps=diagnostics.config.fee_bps,
        slippage_bps=diagnostics.config.slippage_bps,
        data_quality=tuple(quality),
        results=tuple(results),
        methodological_warnings=METHODOLOGICAL_WARNINGS,
    )
    payload = asdict(report)
    payload["metadata"] = {
        "phase": "5F",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "start_time_ms": start_time_ms,
        "end_time_ms": end_time_ms,
        "days_requested": args.days,
        "max_points": args.max_points,
        "research_only": True,
        "oos_already_observed": True,
    }
    _compact_paths(
        payload,
        limit=None if args.include_all_paths else args.path_examples,
    )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = args.output or f"reports/phase5f-{args.strategy}-{stamp}.json"
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
