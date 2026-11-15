from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from app.evaluation.experiment_registry import ExperimentRegistry
from app.evaluation.research_dossier import build_research_dossier


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5H.17 research status dossier"
    )
    parser.add_argument("--registry", default="research/experiment-registry.json")
    parser.add_argument("--reports-root", default="reports/prospective")
    parser.add_argument("--phase5g-root", default="reports/phase5g")
    parser.add_argument("--output", default="reports/research-dossier.json")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    registry = ExperimentRegistry.load(Path(args.registry))
    dossier = build_research_dossier(
        registry=registry,
        reports_root=Path(args.reports_root),
        phase5g_root=Path(args.phase5g_root),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(dossier, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    for item in dossier["experiments"]:
        print(
            f"{item['experiment_id']} | {item['status']} | "
            f"{item['next_allowed_action']}"
        )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
