from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


DAY_MS = 24 * 60 * 60 * 1000


@dataclass(frozen=True)
class SignalScarcity:
    state: str
    elapsed_days: float
    baseline_observations: int
    candidate_observations: int
    candidate_matured: int
    descriptive_only: bool
    detail: str


def evaluate_signal_scarcity(
    report: Mapping[str, Any],
    *,
    frozen_at_ms: int,
    as_of_ms: int,
) -> SignalScarcity:
    if as_of_ms < frozen_at_ms:
        raise ValueError("as_of_ms cannot predate frozen_at_ms")

    baseline = report.get("baseline") or {}
    candidate = report.get("candidate_summary") or report.get("candidate") or {}
    baseline_observations = int(baseline.get("observations", 0))
    candidate_observations = int(candidate.get("observations", 0))
    candidate_matured = int(candidate.get("matured", 0))
    elapsed_days = (as_of_ms - frozen_at_ms) / DAY_MS

    if candidate_matured > 0:
        state = "CANDIDATE_MATURED"
        detail = "At least one candidate observation has matured."
    elif candidate_observations > 0:
        state = "CANDIDATE_SIGNAL_SEEN"
        detail = "Candidate observations exist but none is matured yet."
    else:
        state = "NO_CANDIDATE_SIGNAL"
        detail = (
            "No candidate observation has occurred yet. This is descriptive "
            "only and does not justify changing the frozen rule."
        )

    return SignalScarcity(
        state=state,
        elapsed_days=elapsed_days,
        baseline_observations=baseline_observations,
        candidate_observations=candidate_observations,
        candidate_matured=candidate_matured,
        descriptive_only=True,
        detail=detail,
    )


def scarcity_to_dict(value: SignalScarcity) -> dict[str, Any]:
    return asdict(value)
