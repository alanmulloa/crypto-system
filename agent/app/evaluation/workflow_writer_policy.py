from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence


EXPECTED_WRITERS = (
    ".github/workflows/phase5g-prospective.yml",
    ".github/workflows/phase5h-generic-prospective.yml",
    ".github/workflows/phase5m-campaign-operations.yml",
    ".github/workflows/phase5vz-research-control-plane.yml",
)
SHARED_GROUP = "research-main-writer"


@dataclass(frozen=True)
class WriterPolicyResult:
    path: str
    has_write_permission: bool
    shared_concurrency_group: bool
    cancel_in_progress_disabled: bool
    fetch_depth_zero: bool
    rebase_before_push: bool
    pushes_main: bool
    compliant: bool


def inspect_writer(path: Path) -> WriterPolicyResult:
    text = path.read_text(encoding="utf-8")
    has_write_permission = "contents: write" in text
    shared_group = f"group: {SHARED_GROUP}" in text
    cancel_false = "cancel-in-progress: false" in text
    fetch_depth_zero = "fetch-depth: 0" in text
    rebase_before_push = "git pull --rebase origin main" in text
    pushes_main = "git push origin HEAD:main" in text
    compliant = all(
        (
            has_write_permission,
            shared_group,
            cancel_false,
            fetch_depth_zero,
            rebase_before_push,
            pushes_main,
        )
    )
    return WriterPolicyResult(
        path=str(path),
        has_write_permission=has_write_permission,
        shared_concurrency_group=shared_group,
        cancel_in_progress_disabled=cancel_false,
        fetch_depth_zero=fetch_depth_zero,
        rebase_before_push=rebase_before_push,
        pushes_main=pushes_main,
        compliant=compliant,
    )


def audit_writer_policy(
    *,
    root: Path,
    workflow_paths: Sequence[str] = EXPECTED_WRITERS,
) -> dict[str, Any]:
    results = tuple(inspect_writer(root / path) for path in workflow_paths)
    return {
        "phase": "5T",
        "shared_concurrency_group": SHARED_GROUP,
        "writers": [asdict(item) for item in results],
        "all_compliant": all(item.compliant for item in results),
        "phase6_blocked": True,
    }
