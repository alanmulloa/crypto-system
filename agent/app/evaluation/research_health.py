from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Mapping

from app.evaluation.research_freshness import evaluate_freshness
from app.evaluation.signal_scarcity import evaluate_signal_scarcity


@dataclass(frozen=True)
class ResearchHealth:
    state: str
    phase6_blocked: bool
    automatic_strategy_change: bool
    freshness: Mapping[str, Any]
    scarcity: Mapping[str, Any]
    research_decision: str | None
    recommended_action: str
    detail: str


def build_research_health(
    *,
    latest: Mapping[str, Any] | None,
    decision: Mapping[str, Any] | None,
    frozen_at_ms: int,
    as_of_ms: int,
    as_of: datetime,
    max_age_hours: float = 12.0,
) -> ResearchHealth:
    freshness = evaluate_freshness(
        latest,
        as_of=as_of,
        max_age_hours=max_age_hours,
    )

    if latest is None:
        return ResearchHealth(
            state="ATTENTION_MISSING_EVIDENCE",
            phase6_blocked=True,
            automatic_strategy_change=False,
            freshness=asdict(freshness),
            scarcity={},
            research_decision=(
                str(decision.get("decision")) if decision else None
            ),
            recommended_action="CHECK_COLLECTION_PIPELINE",
            detail="No latest prospective evidence artifact is available.",
        )

    scarcity = evaluate_signal_scarcity(
        latest,
        frozen_at_ms=frozen_at_ms,
        as_of_ms=as_of_ms,
    )
    observed_decision = (
        str(decision.get("decision"))
        if decision and decision.get("decision") is not None
        else None
    )

    if not freshness.fresh:
        state = "ATTENTION_STALE_EVIDENCE"
        action = "CHECK_COLLECTION_PIPELINE"
        detail = "Prospective evidence is stale or missing a valid timestamp."
    elif observed_decision in {"PASS_RESEARCH", "FAIL_RESEARCH", "INCONCLUSIVE"}:
        state = "HUMAN_REVIEW_REQUIRED"
        action = "HUMAN_RESEARCH_REVIEW"
        detail = "A formal research decision requires human review."
    elif scarcity.state == "NO_CANDIDATE_SIGNAL":
        state = "HEALTHY_WAITING_FOR_SIGNAL"
        action = "CONTINUE_COLLECTION"
        detail = (
            "Collection is healthy; no candidate signal has occurred. "
            "Do not alter the frozen definition."
        )
    elif scarcity.state == "CANDIDATE_SIGNAL_SEEN":
        state = "HEALTHY_WAITING_FOR_MATURITY"
        action = "CONTINUE_COLLECTION"
        detail = "Candidate evidence exists and is waiting for maturity."
    else:
        state = "HEALTHY_ACCUMULATING_SAMPLE"
        action = "CONTINUE_COLLECTION"
        detail = "Matured candidate evidence is accumulating."

    return ResearchHealth(
        state=state,
        phase6_blocked=True,
        automatic_strategy_change=False,
        freshness=asdict(freshness),
        scarcity=asdict(scarcity),
        research_decision=observed_decision,
        recommended_action=action,
        detail=detail,
    )


def health_to_dict(value: ResearchHealth) -> dict[str, Any]:
    return asdict(value)
