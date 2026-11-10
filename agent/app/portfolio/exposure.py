from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from app.portfolio.models import LiquidityState, PortfolioSnapshot


@dataclass(frozen=True)
class CustodyExposure:
    source: str
    known_value_usd: float
    known_weight_pct: float


@dataclass(frozen=True)
class PortfolioExposureReport:
    total_value_usd: float
    custody: tuple[CustodyExposure, ...]
    single_source_attributed_usd: float
    multi_source_unattributed_usd: float
    unknown_custody_usd: float
    explicit_illiquid_usd: float
    explicit_illiquid_pct: float
    known_liquid_usd: float
    unknown_liquidity_usd: float


def analyze_exposure(snapshot: PortfolioSnapshot) -> PortfolioExposureReport:
    total = snapshot.total_value_usd
    custody_values: dict[str, float] = defaultdict(float)
    single_source_attributed = 0.0
    multi_source_unattributed = 0.0
    unknown_custody = 0.0

    explicit_illiquid = 0.0
    known_liquid = 0.0
    unknown_liquidity = 0.0

    for position in snapshot.positions:
        sources = tuple(source for source in position.custody_sources if source)
        if len(sources) == 1:
            custody_values[sources[0]] += position.market_value_usd
            single_source_attributed += position.market_value_usd
        elif len(sources) > 1:
            # Do not split value equally: the tracker does not provide per-custodian
            # balances, so an equal split would create false precision.
            multi_source_unattributed += position.market_value_usd
        else:
            unknown_custody += position.market_value_usd

        if position.liquidity_state in {
            LiquidityState.STAKED,
            LiquidityState.POOLED,
            LiquidityState.LOCKED,
        }:
            explicit_illiquid += position.market_value_usd
        elif position.liquidity_state is LiquidityState.LIQUID:
            known_liquid += position.market_value_usd
        else:
            unknown_liquidity += position.market_value_usd

    custody = tuple(
        CustodyExposure(
            source=source,
            known_value_usd=value,
            known_weight_pct=(value / total * 100.0) if total > 0 else 0.0,
        )
        for source, value in sorted(
            custody_values.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    )

    return PortfolioExposureReport(
        total_value_usd=total,
        custody=custody,
        single_source_attributed_usd=single_source_attributed,
        multi_source_unattributed_usd=multi_source_unattributed,
        unknown_custody_usd=unknown_custody,
        explicit_illiquid_usd=explicit_illiquid,
        explicit_illiquid_pct=(explicit_illiquid / total * 100.0) if total > 0 else 0.0,
        known_liquid_usd=known_liquid,
        unknown_liquidity_usd=unknown_liquidity,
    )
