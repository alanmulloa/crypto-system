from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean
from typing import Iterable

from app.evaluation.outcomes import OutcomeObservation
from app.strategies.base import HypothesisDirection, StrategyState


@dataclass(frozen=True)
class OutcomeSummary:
    horizon: str
    observations: int
    directional_observations: int
    avg_raw_return_pct: float | None
    avg_directional_return_pct: float | None
    avg_mfe_pct: float | None
    avg_mae_pct: float | None
    directional_hit_rate_pct: float | None


def _mean(values: list[float]) -> float | None:
    return fmean(values) if values else None


def summarize_outcomes(
    observations: Iterable[OutcomeObservation],
    *,
    horizon: str,
    source: str | None = None,
    strategy: str | None = None,
    state: StrategyState | None = None,
    direction: HypothesisDirection | None = None,
    market_regime: str | None = None,
) -> OutcomeSummary:
    selected = []
    for observation in observations:
        if source is not None and observation.source != source:
            continue
        if strategy is not None and observation.strategy != strategy:
            continue
        if state is not None and observation.state is not state:
            continue
        if direction is not None and observation.direction is not direction:
            continue
        if market_regime is not None:
            value = observation.market_regime.value if observation.market_regime else None
            if value != market_regime:
                continue
        window = observation.window_for(horizon)
        if window is not None:
            selected.append(window)

    raw = [item.raw_return_pct for item in selected]
    directional = [
        item.directional_return_pct
        for item in selected
        if item.directional_return_pct is not None
    ]
    mfe = [item.mfe_pct for item in selected if item.mfe_pct is not None]
    mae = [item.mae_pct for item in selected if item.mae_pct is not None]

    hit_rate = None
    if directional:
        hit_rate = sum(value > 0 for value in directional) / len(directional) * 100.0

    return OutcomeSummary(
        horizon=horizon,
        observations=len(selected),
        directional_observations=len(directional),
        avg_raw_return_pct=_mean(raw),
        avg_directional_return_pct=_mean(directional),
        avg_mfe_pct=_mean(mfe),
        avg_mae_pct=_mean(mae),
        directional_hit_rate_pct=hit_rate,
    )
