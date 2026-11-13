from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class DiscoveryRule:
    feature: str
    bucket: str
    operator: str
    threshold: float | int | str


_PREDEFINED_RULES = (
    DiscoveryRule("score", "85+", ">=", 85.0),
    DiscoveryRule("confidence", "<76", "<", 76.0),
    DiscoveryRule("confidence", "79+", ">=", 79.0),
    DiscoveryRule("rsi_1h", "<=25", "<=", 25.0),
    DiscoveryRule("atr_pct_1h", "<1.5", "<", 1.5),
    DiscoveryRule("atr_pct_1h", "4.5+", ">=", 4.5),
    DiscoveryRule("volume_ratio_1h", "<=0.75", "<=", 0.75),
    DiscoveryRule("volume_ratio_1h", "2.5+", ">=", 2.5),
    DiscoveryRule("ema_distance_pct_1h", "<=-3", "<=", -3.0),
    DiscoveryRule("ema_distance_pct_1h", ">=0", ">=", 0.0),
    DiscoveryRule("ema_spread_pct_1h", "<=-2", "<=", -2.0),
    DiscoveryRule("ema_spread_pct_1h", ">=0.5", ">=", 0.5),
    DiscoveryRule("rsi_15m", "<30", "<", 30.0),
    DiscoveryRule("rsi_15m", "55+", ">=", 55.0),
    DiscoveryRule("ema_distance_pct_15m", "<=-3", "<=", -3.0),
    DiscoveryRule("ema_distance_pct_15m", ">=0", ">=", 0.0),
    DiscoveryRule("rsi_4h", "<40", "<", 40.0),
    DiscoveryRule("rsi_4h", "60+", ">=", 60.0),
    DiscoveryRule("ema_distance_pct_4h", "<=-2", "<=", -2.0),
    DiscoveryRule("ema_distance_pct_4h", ">=2", ">=", 2.0),
    DiscoveryRule(
        "structure_1h",
        "higher_highs_higher_lows",
        "==",
        "higher_highs_higher_lows",
    ),
    DiscoveryRule(
        "structure_1h",
        "lower_highs_lower_lows",
        "==",
        "lower_highs_lower_lows",
    ),
    DiscoveryRule(
        "structure_4h",
        "higher_highs_higher_lows",
        "==",
        "higher_highs_higher_lows",
    ),
    DiscoveryRule(
        "structure_4h",
        "lower_highs_lower_lows",
        "==",
        "lower_highs_lower_lows",
    ),
)

_RULE_BY_KEY = {(rule.feature, rule.bucket): rule for rule in _PREDEFINED_RULES}


def bucket_for_definition(
    *,
    feature: str,
    operator: str,
    threshold: float | int | str,
) -> str | None:
    for rule in _PREDEFINED_RULES:
        if (
            rule.feature == feature
            and rule.operator == operator
            and rule.threshold == threshold
        ):
            return rule.bucket
    return None


@dataclass(frozen=True)
class CandidateProposal:
    id: str
    symbol: str
    strategy: str
    direction: str
    feature: str
    operator: str
    threshold: float | int | str
    outcome_hours: int
    calibration_observations: int
    validation_observations: int
    calibration_average_return_pct: float
    validation_average_return_pct: float
    calibration_uplift_pct_points: float
    validation_uplift_pct_points: float
    recommendation: str = "RESEARCH_CANDIDATE"
    research_only: bool = True
    auto_register: bool = False
    auto_freeze: bool = False


def _slug(value: float | int | str) -> str:
    text = str(value).strip().lower()
    return (
        text.replace("-", "neg")
        .replace(".", "p")
        .replace(" ", "-")
        .replace("/", "-")
    )


def proposal_id(
    *,
    symbol: str,
    feature: str,
    operator: str,
    threshold: float | int | str,
) -> str:
    op = {
        "<=": "lte",
        ">=": "gte",
        "<": "lt",
        ">": "gt",
        "==": "eq",
    }[operator]
    return f"{symbol.lower()}-{feature}-{op}-{_slug(threshold)}"


def discover_from_symbol_report(
    report: Mapping[str, Any],
) -> tuple[CandidateProposal, ...]:
    symbol = str(report["symbol"])
    strategy = str(report["strategy"])
    outcome_hours = int(report["outcome_hours"])
    evidence = report.get("cross_segment_evidence") or []

    proposals: list[CandidateProposal] = []
    for row in evidence:
        feature = str(row["feature"])
        bucket = str(row["bucket"])
        rule = _RULE_BY_KEY.get((feature, bucket))
        if rule is None:
            continue

        sufficient = bool(row.get("sufficient_sample_both"))
        positive_return = bool(row.get("stable_positive_return"))
        positive_uplift = bool(row.get("stable_positive_uplift"))
        if not (sufficient and positive_return and positive_uplift):
            continue

        cal_return = row.get("calibration_average_return_pct")
        val_return = row.get("validation_average_return_pct")
        cal_uplift = row.get("calibration_uplift_pct_points")
        val_uplift = row.get("validation_uplift_pct_points")
        if None in (cal_return, val_return, cal_uplift, val_uplift):
            continue

        proposals.append(
            CandidateProposal(
                id=proposal_id(
                    symbol=symbol,
                    feature=feature,
                    operator=rule.operator,
                    threshold=rule.threshold,
                ),
                symbol=symbol,
                strategy=strategy,
                direction="BUY",
                feature=feature,
                operator=rule.operator,
                threshold=rule.threshold,
                outcome_hours=outcome_hours,
                calibration_observations=int(row["calibration_observations"]),
                validation_observations=int(row["validation_observations"]),
                calibration_average_return_pct=float(cal_return),
                validation_average_return_pct=float(val_return),
                calibration_uplift_pct_points=float(cal_uplift),
                validation_uplift_pct_points=float(val_uplift),
            )
        )

    return tuple(
        sorted(
            proposals,
            key=lambda item: (
                -item.validation_uplift_pct_points,
                -item.validation_average_return_pct,
                -min(item.calibration_observations, item.validation_observations),
                item.id,
            ),
        )
    )


def discover_from_phase5f1_payload(
    payload: Mapping[str, Any],
) -> tuple[CandidateProposal, ...]:
    metadata = payload.get("metadata") or {}
    if metadata.get("phase") != "5F.1":
        raise ValueError("candidate discovery requires a Phase 5F.1 artifact")
    if metadata.get("research_only") is not True:
        raise ValueError("Phase 5F.1 artifact must be research_only")

    proposals = [
        proposal
        for report in payload.get("results") or []
        for proposal in discover_from_symbol_report(report)
    ]
    return tuple(
        sorted(
            proposals,
            key=lambda item: (
                -item.validation_uplift_pct_points,
                -item.validation_average_return_pct,
                item.symbol,
                item.id,
            ),
        )
    )
