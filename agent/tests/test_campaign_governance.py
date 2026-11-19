from app.evaluation.campaign_governance import (
    build_campaign_governance_status,
)
from app.evaluation.campaign_recovery import build_recovery_plan
from app.evaluation.campaign_reproducibility import (
    build_reproducibility_manifest,
    verify_reproducibility_manifest,
)
from app.evaluation.campaign_review_pack import build_campaign_review_pack


def test_recovery_plan_never_mutates_strategy_or_registry():
    plan = build_recovery_plan(
        {
            "incidents": [
                {
                    "severity": "HIGH",
                    "code": "INTERVAL_GAP",
                }
            ]
        }
    )
    assert plan["automatic_recovery"] is False
    assert plan["automatic_strategy_change"] is False
    assert plan["automatic_registry_write"] is False
    assert plan["phase6_blocked"] is True


def test_reproducibility_manifest_verifies_exact_inputs():
    campaign = {"id": "forward", "symbols": ["BTCUSDT"]}
    operations = {
        "campaign_fingerprint_sha256": "a" * 64,
        "phase": "5L.5",
    }
    incidents = {"incident_count": 0, "incidents": []}
    recovery = build_recovery_plan(incidents)
    manifest = build_reproducibility_manifest(
        campaign_payload=campaign,
        latest_operations=operations,
        incidents=incidents,
        recovery=recovery,
    )
    assert verify_reproducibility_manifest(
        manifest,
        campaign_payload=campaign,
        latest_operations=operations,
        incidents=incidents,
        recovery=recovery,
    )


def test_review_pack_blocks_on_critical_incident():
    recovery = {
        "highest_severity": "CRITICAL",
        "actions": [],
    }
    review = build_campaign_review_pack(
        operations={
            "campaign_id": "forward",
            "progress": {"progress_pct": 10.0, "remaining_days": 90},
            "screening_readiness": {"screening_allowed": False},
        },
        incidents={"incident_count": 1},
        recovery=recovery,
        reproducibility={"source_artifacts_immutable": True},
    )
    assert review["state"] == "BLOCKED_CRITICAL_INCIDENT"
    assert review["automatic_screening"] is False
    assert review["phase6_blocked"] is True


def test_governance_never_makes_phase6_eligible():
    status = build_campaign_governance_status(
        review_pack={
            "campaign_id": "forward",
            "state": "COLLECTING",
            "next_action": "CONTINUE_FIXED_WINDOW",
        },
        reproducibility={
            "source_artifacts_immutable": True,
            "automatic_repair": False,
        },
    )
    assert status["operations_hardening_complete"] is True
    assert status["phase6_eligible"] is False
    assert status["phase6_blocked"] is True
