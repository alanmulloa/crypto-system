from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from app.evaluation.campaign_reproducibility import (
    build_reproducibility_manifest,
    load_json,
    verify_reproducibility_manifest,
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5O campaign reproducibility manifest"
    )
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--operations", required=True)
    parser.add_argument("--incidents", required=True)
    parser.add_argument("--recovery", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    campaign = load_json(Path(args.campaign))
    operations = load_json(Path(args.operations))
    incidents = load_json(Path(args.incidents))
    recovery = load_json(Path(args.recovery))
    manifest = build_reproducibility_manifest(
        campaign_payload=campaign,
        latest_operations=operations,
        incidents=incidents,
        recovery=recovery,
    )
    if not verify_reproducibility_manifest(
        manifest,
        campaign_payload=campaign,
        latest_operations=operations,
        incidents=incidents,
        recovery=recovery,
    ):
        raise SystemExit("reproducibility verification failed")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
