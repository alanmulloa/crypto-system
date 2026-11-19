from pathlib import Path

from app.evaluation.workflow_writer_policy import audit_writer_policy


def test_all_research_main_writers_share_one_safe_policy():
    root = Path(__file__).resolve().parents[2]
    payload = audit_writer_policy(root=root)
    assert payload["all_compliant"] is True
    assert payload["shared_concurrency_group"] == "research-main-writer"
    assert payload["phase6_blocked"] is True
