from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from app.evaluation.experiment_registry import ExperimentStatus, ResearchExperiment
from app.evaluation.freeze_manifest import (
    canonical_json_sha256,
    freeze_definition,
)


DEFAULT_MIN_MATURED_OBSERVATIONS = 20
HOUR_MS = 60 * 60 * 1000


@dataclass(frozen=True)
class GenericProspectiveProtocol:
    experiment_id: str
    symbol: str
    strategy: str
    direction: str
    feature: str
    operator: str
    threshold: float | int | str
    frozen_at_ms: int
    outcome_hours: int
    fee_bps: float
    slippage_bps: float
    min_matured_observations: int
    definition_fingerprint_sha256: str
    research_only: bool = True
    phase6_blocked: bool = True
    execution_enabled: bool = False
    testnet_enabled: bool = False
    automatic_promotion: bool = False


def build_generic_protocol(
    *,
    experiment: ResearchExperiment,
    freeze_manifest: Mapping[str, Any],
    min_matured_observations: int = DEFAULT_MIN_MATURED_OBSERVATIONS,
) -> GenericProspectiveProtocol:
    if experiment.status is not ExperimentStatus.FROZEN:
        raise ValueError("generic prospective bootstrap requires FROZEN status")
    if experiment.freeze_at_ms is None:
        raise ValueError("FROZEN experiment requires freeze_at_ms")
    if min_matured_observations <= 0:
        raise ValueError("min_matured_observations must be positive")

    metadata = freeze_manifest.get("metadata") or {}
    if metadata.get("phase") != "5H.9":
        raise ValueError("freeze manifest must be Phase 5H.9")
    if freeze_manifest.get("experiment_id") != experiment.id:
        raise ValueError("freeze manifest experiment_id mismatch")
    if metadata.get("research_only") is not True:
        raise ValueError("freeze manifest must be research_only")
    if metadata.get("phase6_blocked") is not True:
        raise ValueError("freeze manifest must keep phase6_blocked=true")

    expected_definition = freeze_definition(experiment)
    expected_fingerprint = canonical_json_sha256(expected_definition)
    if freeze_manifest.get("frozen_definition") != expected_definition:
        raise ValueError("freeze manifest definition drift detected")
    if freeze_manifest.get("definition_fingerprint_sha256") != expected_fingerprint:
        raise ValueError("freeze manifest definition fingerprint mismatch")

    return GenericProspectiveProtocol(
        experiment_id=experiment.id,
        symbol=experiment.symbol,
        strategy=experiment.strategy,
        direction=experiment.direction,
        feature=experiment.feature,
        operator=experiment.operator,
        threshold=experiment.threshold,
        frozen_at_ms=experiment.freeze_at_ms,
        outcome_hours=experiment.outcome_hours,
        fee_bps=experiment.fee_bps,
        slippage_bps=experiment.slippage_bps,
        min_matured_observations=min_matured_observations,
        definition_fingerprint_sha256=expected_fingerprint,
    )


def protocol_to_dict(protocol: GenericProspectiveProtocol) -> dict[str, Any]:
    return asdict(protocol)


def protocol_from_bootstrap(
    payload: Mapping[str, Any],
) -> GenericProspectiveProtocol:
    metadata = payload.get("metadata") or {}
    if metadata.get("phase") != "5H.10":
        raise ValueError("bootstrap artifact must be Phase 5H.10")
    if metadata.get("research_only") is not True:
        raise ValueError("bootstrap must be research_only")
    if metadata.get("phase6_blocked") is not True:
        raise ValueError("bootstrap must keep phase6_blocked=true")
    if metadata.get("execution_enabled") is not False:
        raise ValueError("bootstrap must keep execution_enabled=false")
    if metadata.get("testnet_enabled") is not False:
        raise ValueError("bootstrap must keep testnet_enabled=false")
    if metadata.get("automatic_promotion") is not False:
        raise ValueError("bootstrap must keep automatic_promotion=false")
    return GenericProspectiveProtocol(**dict(payload["protocol"]))


def _observation_key(item: Mapping[str, Any]) -> tuple[str, str, int]:
    return (
        str(item["cohort"]),
        str(item["symbol"]),
        int(item["signal_timestamp_ms"]),
    )


def validate_generic_report(
    report: Mapping[str, Any],
    *,
    protocol: GenericProspectiveProtocol,
) -> None:
    metadata = report.get("metadata") or {}
    if metadata.get("phase") != "5H.10-prospective":
        raise ValueError("generic prospective report phase changed")
    if metadata.get("research_only") is not True:
        raise ValueError("generic prospective report must be research_only")
    if metadata.get("phase6_blocked") is not True:
        raise ValueError("generic prospective report must keep phase6_blocked=true")
    if metadata.get("execution_enabled") is not False:
        raise ValueError("execution_enabled must remain false")
    if metadata.get("testnet_enabled") is not False:
        raise ValueError("testnet_enabled must remain false")
    if metadata.get("automatic_promotion") is not False:
        raise ValueError("automatic_promotion must remain false")

    frozen = report.get("frozen_experiment") or {}
    expected = protocol_to_dict(protocol)
    for key in (
        "experiment_id",
        "symbol",
        "strategy",
        "direction",
        "feature",
        "operator",
        "threshold",
        "frozen_at_ms",
        "outcome_hours",
        "fee_bps",
        "slippage_bps",
        "min_matured_observations",
        "definition_fingerprint_sha256",
    ):
        if frozen.get(key) != expected[key]:
            raise ValueError(f"frozen experiment changed: {key}")

    for item in report.get("observations") or []:
        if item.get("symbol") != protocol.symbol:
            raise ValueError("observation symbol changed")
        signal_ms = int(item["signal_timestamp_ms"])
        if signal_ms <= protocol.frozen_at_ms:
            raise ValueError("observation is not strictly post-freeze")

        status = item.get("status")
        if status not in {"NO_ENTRY", "PENDING", "MATURED"}:
            raise ValueError("invalid observation status")
        if status != "MATURED":
            continue

        entry_ms = item.get("entry_timestamp_ms")
        outcome_ms = item.get("outcome_timestamp_ms")
        if entry_ms is None or outcome_ms is None:
            raise ValueError("matured observation is missing timestamps")
        required = int(entry_ms) + protocol.outcome_hours * HOUR_MS - 1
        if int(outcome_ms) < required:
            raise ValueError("matured observation has incomplete outcome horizon")
        if item.get("net_return_pct") is None:
            raise ValueError("matured observation is missing net return")
        if item.get("positive_return") is None:
            raise ValueError("matured observation is missing positive_return")


_IMMUTABLE_OBSERVATION_FIELDS = (
    "cohort",
    "symbol",
    "signal_timestamp_ms",
    "entry_timestamp_ms",
    "entry_market_price",
    "feature_value",
)


def assert_generic_history_compatible(
    previous: Mapping[str, Any],
    current: Mapping[str, Any],
    *,
    protocol: GenericProspectiveProtocol,
) -> None:
    validate_generic_report(previous, protocol=protocol)
    validate_generic_report(current, protocol=protocol)

    old_by_key = {
        _observation_key(item): item
        for item in previous.get("observations") or []
    }
    new_by_key = {
        _observation_key(item): item
        for item in current.get("observations") or []
    }

    missing = sorted(set(old_by_key) - set(new_by_key))
    if missing:
        raise ValueError(f"previous observations disappeared: {missing}")

    for key, old in old_by_key.items():
        new = new_by_key[key]
        for field in _IMMUTABLE_OBSERVATION_FIELDS:
            if old.get(field) != new.get(field):
                raise ValueError(
                    f"observation mutated immutable field {field}: {key}"
                )

        old_status = old.get("status")
        new_status = new.get("status")
        if old_status == "PENDING" and new_status == "MATURED":
            continue
        if old_status != new_status:
            raise ValueError(f"invalid observation status transition: {key}")

        if old_status == "MATURED":
            for field in (
                "outcome_timestamp_ms",
                "gross_return_pct",
                "net_return_pct",
                "positive_return",
            ):
                if old.get(field) != new.get(field):
                    raise ValueError(
                        f"matured observation mutated {field}: {key}"
                    )
