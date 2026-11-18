from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.evaluation.experiment_registry import ResearchExperiment
from app.evaluation.freeze_manifest import (
    canonical_json_sha256,
    freeze_definition,
)


_PHASE_BY_ARTIFACT = {
    "calibration": "5H.6",
    "validation": "5H.7",
    "freeze_review": "5H.8",
    "manifest": "5H.9",
    "bootstrap": "5H.10",
    "latest": "5H.10-prospective",
    "review": "5H.11-generic-monitoring-review",
    "decision": "5H.11-generic-prospective-decision",
}


@dataclass(frozen=True)
class AuditCheck:
    name: str
    passed: bool
    detail: str


def _metadata(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    value = payload.get("metadata")
    return value if isinstance(value, Mapping) else {}


def build_lineage_audit(
    *,
    experiment: ResearchExperiment,
    artifacts: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    checks: list[AuditCheck] = []
    missing = [
        name for name in _PHASE_BY_ARTIFACT if name not in artifacts
    ]

    for name, expected_phase in _PHASE_BY_ARTIFACT.items():
        payload = artifacts.get(name)
        if payload is None:
            continue

        if name in {"review", "decision"}:
            phase = payload.get("phase")
        else:
            phase = _metadata(payload).get("phase")
        checks.append(
            AuditCheck(
                name=f"{name}_phase",
                passed=phase == expected_phase,
                detail=f"expected={expected_phase}, observed={phase}",
            )
        )

    definition = freeze_definition(experiment)
    fingerprint = canonical_json_sha256(definition)

    manifest = artifacts.get("manifest")
    if manifest is not None:
        checks.append(
            AuditCheck(
                name="manifest_experiment_id",
                passed=manifest.get("experiment_id") == experiment.id,
                detail="manifest experiment id must match registry",
            )
        )
        checks.append(
            AuditCheck(
                name="manifest_definition_fingerprint",
                passed=(
                    manifest.get("definition_fingerprint_sha256")
                    == fingerprint
                ),
                detail="manifest fingerprint must match current locked definition",
            )
        )

    bootstrap = artifacts.get("bootstrap")
    if bootstrap is not None:
        protocol = bootstrap.get("protocol") or {}
        checks.append(
            AuditCheck(
                name="bootstrap_experiment_id",
                passed=protocol.get("experiment_id") == experiment.id,
                detail="bootstrap experiment id must match registry",
            )
        )
        checks.append(
            AuditCheck(
                name="bootstrap_definition_fingerprint",
                passed=(
                    protocol.get("definition_fingerprint_sha256")
                    == fingerprint
                ),
                detail="bootstrap fingerprint must match current definition",
            )
        )

    latest = artifacts.get("latest")
    if latest is not None:
        frozen = latest.get("frozen_experiment") or {}
        checks.append(
            AuditCheck(
                name="latest_experiment_id",
                passed=frozen.get("experiment_id") == experiment.id,
                detail="prospective report experiment id must match registry",
            )
        )
        checks.append(
            AuditCheck(
                name="latest_definition_fingerprint",
                passed=(
                    frozen.get("definition_fingerprint_sha256")
                    == fingerprint
                ),
                detail="prospective report fingerprint must remain frozen",
            )
        )
        checks.append(
            AuditCheck(
                name="latest_phase6_blocked",
                passed=_metadata(latest).get("phase6_blocked") is True,
                detail="prospective report must keep Phase 6 blocked",
            )
        )

    decision = artifacts.get("decision")
    if decision is not None:
        checks.append(
            AuditCheck(
                name="decision_phase6_blocked",
                passed=decision.get("phase6_blocked") is True,
                detail="research decision must keep Phase 6 blocked",
            )
        )
        checks.append(
            AuditCheck(
                name="decision_no_auto_promotion",
                passed=(
                    decision.get("automatic_phase6_promotion") is False
                ),
                detail="research decision cannot auto-promote to Phase 6",
            )
        )

    invalid = [check for check in checks if not check.passed]
    status = (
        "INVALID"
        if invalid
        else "COMPLETE_VALID"
        if not missing
        else "PARTIAL_VALID"
    )
    return {
        "phase": "5H.16",
        "experiment_id": experiment.id,
        "status": status,
        "definition_fingerprint_sha256": fingerprint,
        "checks": [check.__dict__ for check in checks],
        "missing_artifacts": missing,
        "phase6_blocked": True,
    }
