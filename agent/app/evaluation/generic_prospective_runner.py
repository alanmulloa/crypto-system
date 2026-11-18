from __future__ import annotations

from datetime import datetime, timezone
from statistics import fmean
from typing import Any, Mapping, Sequence

from app.evaluation.generic_signal_evaluator import (
    assessment_for,
    baseline_matches,
    candidate_matches,
    feature_value,
)
from app.evaluation.historical import HistoricalPoint
from app.evaluation.prospective_bootstrap import (
    GenericProspectiveProtocol,
    HOUR_MS,
    protocol_to_dict,
    validate_generic_report,
)
from app.market.types import Candle


def _median(values: Sequence[float]) -> float | None:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def _entry_candle(
    point: HistoricalPoint,
    candles: Sequence[Candle],
    *,
    strategy: str,
) -> Candle | None:
    assessment = assessment_for(point, strategy)
    if assessment is None:
        return None
    candle = next(
        (item for item in candles if item.open_time_ms > point.timestamp_ms),
        None,
    )
    if candle is None:
        return None
    if assessment.entry_low is None or assessment.entry_high is None:
        return None
    if not assessment.entry_low <= candle.open <= assessment.entry_high:
        return None
    return candle


def _net_return(
    entry_market_price: float,
    exit_market_price: float,
    *,
    fee_bps: float,
    slippage_bps: float,
) -> float:
    fee_rate = fee_bps / 10_000.0
    entry = entry_market_price * (1.0 + slippage_bps / 10_000.0)
    exit_price = exit_market_price * (1.0 - slippage_bps / 10_000.0)
    notional = 100.0
    quantity = notional / entry
    entry_fee = notional * fee_rate
    exit_gross = quantity * exit_price
    exit_fee = exit_gross * fee_rate
    pnl = exit_gross - exit_fee - notional - entry_fee
    return pnl / (notional + entry_fee) * 100.0


def _observe(
    point: HistoricalPoint,
    *,
    protocol: GenericProspectiveProtocol,
    candles: Sequence[Candle],
    as_of_ms: int,
    cohort: str,
) -> dict[str, Any]:
    entry = _entry_candle(
        point,
        candles,
        strategy=protocol.strategy,
    )
    value = feature_value(
        point,
        strategy=protocol.strategy,
        feature=protocol.feature,
    )
    base = {
        "cohort": cohort,
        "symbol": point.candidate.symbol,
        "signal_timestamp_ms": point.timestamp_ms,
        "feature_value": value,
    }
    if entry is None:
        return {
            **base,
            "entry_timestamp_ms": None,
            "entry_market_price": None,
            "status": "NO_ENTRY",
            "outcome_timestamp_ms": None,
            "gross_return_pct": None,
            "net_return_pct": None,
            "positive_return": None,
        }

    target_ms = entry.open_time_ms + protocol.outcome_hours * HOUR_MS
    outcome = next(
        (
            candle
            for candle in candles
            if candle.close_time_ms >= target_ms - 1
            and candle.open_time_ms >= entry.open_time_ms
        ),
        None,
    )
    if outcome is None or outcome.close_time_ms > as_of_ms:
        return {
            **base,
            "entry_timestamp_ms": entry.open_time_ms,
            "entry_market_price": entry.open,
            "status": "PENDING",
            "outcome_timestamp_ms": target_ms,
            "gross_return_pct": None,
            "net_return_pct": None,
            "positive_return": None,
        }

    gross = (outcome.close / entry.open - 1.0) * 100.0
    net = _net_return(
        entry.open,
        outcome.close,
        fee_bps=protocol.fee_bps,
        slippage_bps=protocol.slippage_bps,
    )
    return {
        **base,
        "entry_timestamp_ms": entry.open_time_ms,
        "entry_market_price": entry.open,
        "status": "MATURED",
        "outcome_timestamp_ms": outcome.close_time_ms,
        "gross_return_pct": gross,
        "net_return_pct": net,
        "positive_return": net > 0,
    }


def _summary(cohort: str, observations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    selected = [item for item in observations if item["cohort"] == cohort]
    matured = [
        item
        for item in selected
        if item["status"] == "MATURED" and item["net_return_pct"] is not None
    ]
    returns = [float(item["net_return_pct"]) for item in matured]
    return {
        "cohort": cohort,
        "observations": len(selected),
        "matured": len(matured),
        "pending": sum(item["status"] == "PENDING" for item in selected),
        "average_net_return_pct": fmean(returns) if returns else None,
        "median_net_return_pct": _median(returns),
        "positive_return_rate_pct": (
            sum(value > 0 for value in returns) / len(returns) * 100.0
            if returns
            else None
        ),
    }


def run_generic_prospective(
    *,
    protocol: GenericProspectiveProtocol,
    points: Sequence[HistoricalPoint],
    candles_by_interval: Mapping[str, Sequence[Candle]],
    as_of_ms: int,
    created_at: str | None = None,
) -> dict[str, Any]:
    candles = candles_by_interval.get("1h")
    if not candles:
        raise ValueError("1h candles required")
    if as_of_ms <= protocol.frozen_at_ms:
        raise ValueError("as_of_ms must be after frozen_at_ms")

    observations: list[dict[str, Any]] = []
    for point in sorted(points, key=lambda item: item.timestamp_ms):
        if point.timestamp_ms <= protocol.frozen_at_ms:
            continue
        if point.timestamp_ms > as_of_ms:
            continue
        if not baseline_matches(point, protocol=protocol):
            continue
        observations.append(
            _observe(
                point,
                protocol=protocol,
                candles=candles,
                as_of_ms=as_of_ms,
                cohort="baseline",
            )
        )
        if candidate_matches(point, protocol=protocol):
            observations.append(
                _observe(
                    point,
                    protocol=protocol,
                    candles=candles,
                    as_of_ms=as_of_ms,
                    cohort="candidate",
                )
            )

    baseline = _summary("baseline", observations)
    candidate = _summary("candidate", observations)
    uplift = None
    if (
        baseline["average_net_return_pct"] is not None
        and candidate["average_net_return_pct"] is not None
    ):
        uplift = (
            candidate["average_net_return_pct"]
            - baseline["average_net_return_pct"]
        )

    report = {
        "metadata": {
            "phase": "5H.10-prospective",
            "created_at": created_at
            or datetime.now(timezone.utc).isoformat(),
            "research_only": True,
            "phase6_blocked": True,
            "execution_enabled": False,
            "testnet_enabled": False,
            "automatic_promotion": False,
        },
        "as_of_ms": as_of_ms,
        "frozen_experiment": protocol_to_dict(protocol),
        "baseline": baseline,
        "candidate_summary": candidate,
        "uplift_vs_baseline_pct_points": uplift,
        "sample_ready": (
            candidate["matured"] >= protocol.min_matured_observations
        ),
        "observations": observations,
    }
    validate_generic_report(report, protocol=protocol)
    return report
