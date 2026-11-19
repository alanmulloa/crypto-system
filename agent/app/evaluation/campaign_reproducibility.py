from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


def canonical_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_reproducibility_manifest(
    *,
    campaign_payload: Mapping[str, Any],
    latest_operations: Mapping[str, Any],
    incidents: Mapping[str, Any],
    recovery: Mapping[str, Any],
) -> dict[str, Any]:
    campaign_id = str(campaign_payload.get("id") or "")
    if not campaign_id:
        raise ValueError("campaign id is required")

    expected_fingerprint = latest_operations.get(
        "campaign_fingerprint_sha256"
    )
    if not isinstance(expected_fingerprint, str) or not expected_fingerprint:
        raise ValueError("latest operations fingerprint missing")

    return {
        "phase": "5O",
        "campaign_id": campaign_id,
        "campaign_definition_sha256": canonical_sha256(campaign_payload),
        "operations_sha256": canonical_sha256(latest_operations),
        "incidents_sha256": canonical_sha256(incidents),
        "recovery_sha256": canonical_sha256(recovery),
        "campaign_fingerprint_sha256": expected_fingerprint,
        "research_only": True,
        "source_artifacts_immutable": True,
        "automatic_repair": False,
        "phase6_blocked": True,
    }


def verify_reproducibility_manifest(
    manifest: Mapping[str, Any],
    *,
    campaign_payload: Mapping[str, Any],
    latest_operations: Mapping[str, Any],
    incidents: Mapping[str, Any],
    recovery: Mapping[str, Any],
) -> bool:
    checks = {
        "campaign_definition_sha256": canonical_sha256(campaign_payload),
        "operations_sha256": canonical_sha256(latest_operations),
        "incidents_sha256": canonical_sha256(incidents),
        "recovery_sha256": canonical_sha256(recovery),
    }
    return all(manifest.get(key) == value for key, value in checks.items())


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
