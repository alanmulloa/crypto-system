from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence
import json

from app.evaluation.backtest import BacktestConfig, BacktestSimulator
from app.evaluation.historical import HistoricalSanityRunner
from app.evaluation.outcomes import OutcomeEvaluator
from app.evaluation.validation import (
    StrategyValidationReport,
    TemporalSplitConfig,
    TemporalValidator,
)
from app.market.binance_public import BinancePublicClient, INTERVAL_MS
from app.market.types import Candle


EVIDENCE_INTERVALS = ("15m", "1h", "4h", "1d")
DEFAULT_EVIDENCE_SYMBOLS = (
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "SOLUSDT",
    "XRPUSDT",
)


@dataclass(frozen=True)
class IntervalQuality:
    interval: str
    candles: int
    first_open_time_ms: int | None
    last_close_time_ms: int | None
    duplicate_open_times: int
    gap_count: int


@dataclass(frozen=True)
class SymbolEvidence:
    symbol: str
    points: int
    interval_quality: tuple[IntervalQuality, ...]
    validations: tuple[StrategyValidationReport, ...]


@dataclass(frozen=True)
class EvidenceRun:
    created_at: str
    start_time_ms: int
    end_time_ms: int
    symbols: tuple[str, ...]
    days_requested: int
    max_points: int | None
    results: tuple[SymbolEvidence, ...]


def _quality(interval: str, candles: Sequence[Candle]) -> IntervalQuality:
    if not candles:
        return IntervalQuality(interval, 0, None, None, 0, 0)

    opens = [candle.open_time_ms for candle in candles]
    duplicate_count = len(opens) - len(set(opens))
    step = INTERVAL_MS[interval]
    gap_count = sum(
        1
        for previous, current in zip(opens, opens[1:])
        if current - previous > step
    )
    return IntervalQuality(
        interval=interval,
        candles=len(candles),
        first_open_time_ms=candles[0].open_time_ms,
        last_close_time_ms=candles[-1].close_time_ms,
        duplicate_open_times=duplicate_count,
        gap_count=gap_count,
    )


class RealEvidenceRunner:
    def __init__(
        self,
        *,
        client: BinancePublicClient | None = None,
        historical_runner: HistoricalSanityRunner | None = None,
        validator: TemporalValidator | None = None,
    ):
        self.client = client or BinancePublicClient()
        self.historical_runner = historical_runner or HistoricalSanityRunner(
            min_candles=60,
            analysis_candles=250,
        )
        self.validator = validator or TemporalValidator(
            backtest_simulator=BacktestSimulator(
                BacktestConfig(
                    initial_cash_usd=10_000,
                    notional_usd=100,
                    fee_bps=10,
                    slippage_bps=5,
                    max_holding_ms=24 * 60 * 60 * 1000,
                    require_entry_range=True,
                )
            ),
            outcome_evaluator=OutcomeEvaluator(),
            split_config=TemporalSplitConfig(
                calibration_ratio=0.60,
                validation_ratio=0.20,
                out_of_sample_ratio=0.20,
                min_points_per_segment=20,
            ),
            outcome_horizon="24h",
        )

    def fetch_symbol_history(
        self,
        *,
        symbol: str,
        start_time_ms: int,
        end_time_ms: int,
    ) -> dict[str, tuple[Candle, ...]]:
        return {
            interval: tuple(
                self.client.historical_klines(
                    symbol,
                    interval,
                    start_time_ms=start_time_ms,
                    end_time_ms=end_time_ms,
                    page_limit=1000,
                )
            )
            for interval in EVIDENCE_INTERVALS
        }

    def run_symbol(
        self,
        *,
        symbol: str,
        start_time_ms: int,
        end_time_ms: int,
        max_points: int | None = None,
    ) -> SymbolEvidence:
        history = self.fetch_symbol_history(
            symbol=symbol,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
        )
        quality = tuple(_quality(interval, history[interval]) for interval in EVIDENCE_INTERVALS)

        daily = history["1d"]
        if len(daily) < self.historical_runner.min_candles:
            raise ValueError(
                f"{symbol} has only {len(daily)} daily candles; "
                f"need at least {self.historical_runner.min_candles}"
            )

        quote_asset = "USDT" if symbol.endswith("USDT") else ""
        base_asset = symbol[: -len(quote_asset)] if quote_asset else symbol
        points = self.historical_runner.run(
            symbol=symbol,
            base_asset=base_asset,
            quote_asset=quote_asset,
            candles_by_interval=history,
            anchor_interval="1h",
            max_points=max_points,
        )
        if len(points) < self.validator.split_config.min_points_per_segment * 3:
            raise ValueError(
                f"{symbol} produced only {len(points)} evaluable points; "
                "not enough for temporal validation"
            )

        validations = self.validator.validate_all_strategies(
            points=points,
            candles_by_interval=history,
        )
        return SymbolEvidence(
            symbol=symbol,
            points=len(points),
            interval_quality=quality,
            validations=validations,
        )

    def run(
        self,
        *,
        symbols: Sequence[str],
        days: int,
        end_time_ms: int | None = None,
        max_points: int | None = None,
    ) -> EvidenceRun:
        if days < 90:
            raise ValueError("real evidence run requires at least 90 days")
        normalized = tuple(dict.fromkeys(symbol.upper() for symbol in symbols if symbol.strip()))
        if not normalized:
            raise ValueError("at least one symbol is required")

        end_ms = end_time_ms or self.client.now_ms()
        start_ms = end_ms - days * INTERVAL_MS["1d"]
        results = tuple(
            self.run_symbol(
                symbol=symbol,
                start_time_ms=start_ms,
                end_time_ms=end_ms,
                max_points=max_points,
            )
            for symbol in normalized
        )
        return EvidenceRun(
            created_at=datetime.now(timezone.utc).isoformat(),
            start_time_ms=start_ms,
            end_time_ms=end_ms,
            symbols=normalized,
            days_requested=days,
            max_points=max_points,
            results=results,
        )


def write_evidence_json(report: EvidenceRun, output: str | Path) -> Path:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    return path
