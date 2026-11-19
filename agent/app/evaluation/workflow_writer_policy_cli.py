from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from app.evaluation.workflow_writer_policy import audit_writer_policy


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5T main-writer workflow policy audit"
    )
    parser.add_argument("--root", default="..")
    parser.add_argument(
        "--output",
        default="reports/phase5t/writer-policy.json",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    payload = audit_writer_policy(root=Path(args.root))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"all_compliant={payload['all_compliant']}")
    print(output)
    return 0 if payload["all_compliant"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
