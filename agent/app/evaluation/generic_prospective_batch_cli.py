from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable, Sequence

from app.evaluation.experiment_registry import (
    ExperimentRegistry,
    ExperimentStatus,
)
from app.evaluation.generic_prospective_runner_cli import build_public_report
from app.evaluation.prospective_bootstrap import (
    assert_protocol_matches_experiment,
    protocol_from_bootstrap,
)
from app.evaluation.prospective_collection_generic import collect_generic_report
from app.evaluation.prospective_decision_generic import build_generic_decision
from app.evaluation.prospective_review_generic import build_generic_review
from app.evaluation.research_experiment_planner import (
    LEGACY_PHASE5G_EXPERIMENT_ID,
)


ReportBuilder = Callable[..., dict]


def run_batch(
    *,
    registry: ExperimentRegistry,
    reports_root: Path,
    report_builder: ReportBuilder = build_public_report,
) -> dict:
    results: list[dict] = []
    for experiment in sorted(registry.experiments, key=lambda item: item.id):
        if experiment.id == LEGACY_PHASE5G_EXPERIMENT_ID:
            results.append(
                {
                    "experiment_id": experiment.id,
                    "result": "LEGACY_PHASE5G_UNCHANGED",
                }
            )
            continue
        if experiment.status is not ExperimentStatus.PROSPECTIVE:
            continue

        root = reports_root / experiment.id
        bootstrap_path = root / "bootstrap.json"
        if not bootstrap_path.exists():
            results.append(
                {
                    "experiment_id": experiment.id,
                    "result": "MISSING_BOOTSTRAP",
                }
            )
            continue

        bootstrap = json.loads(bootstrap_path.read_text(encoding="utf-8"))
        protocol = protocol_from_bootstrap(bootstrap)
        assert_protocol_matches_experiment(protocol, experiment)

        fresh = root / "fresh.json"
        latest = root / "latest.json"
        history = root / "history"
        review_path = root / "review.json"
        decision_path = root / "decision.json"

        report = report_builder(bootstrap_payload=bootstrap)
        root.mkdir(parents=True, exist_ok=True)
        fresh.write_text(
            json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        collect_generic_report(
            fresh_report=fresh,
            bootstrap_artifact=bootstrap_path,
            latest_report=latest,
            history_dir=history,
        )
        fresh.unlink(missing_ok=True)

        review = build_generic_review(report, protocol=protocol)
        decision = build_generic_decision(report, protocol=protocol)
        review_path.write_text(
            json.dumps(review, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        decision_path.write_text(
            json.dumps(decision, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        results.append(
            {
                "experiment_id": experiment.id,
                "result": "COLLECTED",
                "state": review["state"],
                "decision": decision["decision"],
                "phase6_blocked": True,
            }
        )

    return {
        "phase": "5H.15",
        "phase6_blocked": True,
        "automatic_phase6_promotion": False,
        "results": results,
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5H.15 generic prospective batch orchestrator"
    )
    parser.add_argument("--registry", default="research/experiment-registry.json")
    parser.add_argument("--reports-root", default="reports/prospective")
    parser.add_argument(
        "--summary-output",
        default="reports/prospective/batch-summary.json",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    registry = ExperimentRegistry.load(Path(args.registry))
    try:
        summary = run_batch(
            registry=registry,
            reports_root=Path(args.reports_root),
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    output = Path(args.summary_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    for item in summary["results"]:
        print(f"{item['experiment_id']} | {item['result']}")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
