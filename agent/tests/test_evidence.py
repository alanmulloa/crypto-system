from dataclasses import dataclass

from app.evaluation.evidence import (
    EvidenceRun,
    RealEvidenceRunner,
    _quality,
    write_evidence_json,
)
from app.market.binance_public import INTERVAL_MS
from app.market.types import Candle


def candle(index, interval):
    step = INTERVAL_MS[interval]
    open_time = index * step
    return Candle(
        open_time_ms=open_time,
        open=100,
        high=101,
        low=99,
        close=100,
        volume=1000,
        close_time_ms=open_time + step - 1,
    )


def test_quality_detects_gaps_without_failing_dataset():
    items = (candle(0, "1h"), candle(1, "1h"), candle(3, "1h"))
    quality = _quality("1h", items)
    assert quality.candles == 3
    assert quality.gap_count == 1
    assert quality.duplicate_open_times == 0


@dataclass
class FakeHistoricalRunner:
    min_candles: int = 2

    def run(self, **kwargs):
        return tuple(range(6))


@dataclass
class FakeSplitConfig:
    min_points_per_segment: int = 2


class FakeValidator:
    split_config = FakeSplitConfig()

    def validate_all_strategies(self, **kwargs):
        return ()


class FakeClient:
    now_ms = staticmethod(lambda: 100 * INTERVAL_MS["1d"])

    def historical_klines(
        self,
        symbol,
        interval,
        *,
        start_time_ms,
        end_time_ms,
        page_limit,
    ):
        count = 4 if interval == "1d" else 10
        return [candle(index, interval) for index in range(count)]


def test_real_evidence_runner_wires_history_points_and_validation():
    runner = RealEvidenceRunner(
        client=FakeClient(),
        historical_runner=FakeHistoricalRunner(),
        validator=FakeValidator(),
    )
    result = runner.run_symbol(
        symbol="BTCUSDT",
        start_time_ms=0,
        end_time_ms=100 * INTERVAL_MS["1d"],
        max_points=6,
    )
    assert result.symbol == "BTCUSDT"
    assert result.points == 6
    assert len(result.interval_quality) == 4


def test_write_evidence_json_creates_parent_directory(tmp_path):
    report = EvidenceRun(
        created_at="2026-11-10T00:00:00+00:00",
        start_time_ms=0,
        end_time_ms=1,
        symbols=("BTCUSDT",),
        days_requested=90,
        max_points=60,
        results=(),
    )
    path = write_evidence_json(report, tmp_path / "nested" / "report.json")
    assert path.exists()
    assert "BTCUSDT" in path.read_text(encoding="utf-8")
