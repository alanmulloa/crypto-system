from app.config import Settings
from app.evaluation.phase6_approval import build_pending_approval
from app.evaluation.phase6_execution_boundary import build_execution_boundary
from app.evaluation.phase6_readiness import build_phase6_readiness
from app.evaluation.phase6_research_gate import build_research_gate_snapshot
from app.evaluation.phase6_risk_preflight import build_risk_preflight
from app.evaluation.phase6_testnet_dry_run import build_testnet_dry_run_plan


def test_not_ready_research_stays_blocked():
    research = build_research_gate_snapshot(
        experiment_id="xrp",
        decision={"decision": "NOT_READY", "research_gate_passed": False},
        review={"sample_ready": False},
    )
    readiness = build_phase6_readiness(
        research=research,
        risk=build_risk_preflight(Settings()),
        boundary=build_execution_boundary(),
        approval=build_pending_approval("xrp"),
    )
    assert readiness.state == "BLOCKED_RESEARCH"
    assert readiness.phase6_eligible is False
    assert readiness.phase6_blocked is True


def test_pass_research_requires_human_approval():
    research = build_research_gate_snapshot(
        experiment_id="candidate",
        decision={
            "decision": "PASS_RESEARCH",
            "research_gate_passed": True,
        },
        review={"sample_ready": True},
    )
    readiness = build_phase6_readiness(
        research=research,
        risk=build_risk_preflight(Settings()),
        boundary=build_execution_boundary(),
        approval=build_pending_approval("candidate"),
    )
    assert readiness.state == "READY_FOR_HUMAN_APPROVAL"
    assert readiness.automatic_activation is False


def test_dry_run_never_submits_orders():
    research = build_research_gate_snapshot(
        experiment_id="candidate",
        decision={"decision": "NOT_READY", "research_gate_passed": False},
        review={"sample_ready": False},
    )
    readiness = build_phase6_readiness(
        research=research,
        risk=build_risk_preflight(Settings()),
        boundary=build_execution_boundary(),
        approval=build_pending_approval("candidate"),
    )
    plan = build_testnet_dry_run_plan(
        readiness=readiness,
        settings=Settings(),
    )
    assert plan.private_api_calls is False
    assert plan.orders_submitted is False
    assert plan.credentials_written is False
    assert plan.phase6_blocked is True
