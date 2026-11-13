import json

from app.evaluation.experiment_registry import ExperimentStatus, ResearchExperiment
from app.evaluation.freeze_manifest import canonical_json_sha256, freeze_definition
from app.evaluation.prospective_bootstrap import build_generic_protocol, protocol_to_dict
from app.evaluation.prospective_collection_generic import collect_generic_report


def test_generic_collection_persists_immutable_snapshot(tmp_path):
    exp = ResearchExperiment(
        id="future",
        symbol="BTCUSDT",
        strategy="mean_reversion",
        direction="BUY",
        feature="volume_ratio_1h",
        operator="<=",
        threshold=0.75,
        calibration_period=None,
        validation_period=None,
        freeze_at_ms=1000,
        outcome_hours=24,
        fee_bps=10.0,
        slippage_bps=5.0,
        status=ExperimentStatus.FROZEN,
        decision=None,
        artifact_path="reports/research/future/",
    )
    definition = freeze_definition(exp)
    protocol = build_generic_protocol(
        experiment=exp,
        freeze_manifest={
            "metadata": {
                "phase": "5H.9",
                "research_only": True,
                "phase6_blocked": True,
            },
            "experiment_id": exp.id,
            "frozen_definition": definition,
            "definition_fingerprint_sha256": canonical_json_sha256(definition),
        },
    )
    bootstrap = tmp_path / "bootstrap.json"
    fresh = tmp_path / "fresh.json"
    latest = tmp_path / "latest.json"
    history = tmp_path / "history"

    bootstrap.write_text(
        json.dumps(
            {
                "metadata": {
                    "phase": "5H.10",
                    "research_only": True,
                    "phase6_blocked": True,
                    "execution_enabled": False,
                    "testnet_enabled": False,
                    "automatic_promotion": False,
                },
                "protocol": protocol_to_dict(protocol),
            }
        ),
        encoding="utf-8",
    )
    fresh.write_text(
        json.dumps(
            {
                "metadata": {
                    "phase": "5H.10-prospective",
                    "created_at": "2026-11-13T00:00:00+00:00",
                    "research_only": True,
                    "phase6_blocked": True,
                    "execution_enabled": False,
                    "testnet_enabled": False,
                    "automatic_promotion": False,
                },
                "frozen_experiment": {
                    "experiment_id": protocol.experiment_id,
                    "symbol": protocol.symbol,
                    "strategy": protocol.strategy,
                    "direction": protocol.direction,
                    "feature": protocol.feature,
                    "operator": protocol.operator,
                    "threshold": protocol.threshold,
                    "frozen_at_ms": protocol.frozen_at_ms,
                    "outcome_hours": protocol.outcome_hours,
                    "fee_bps": protocol.fee_bps,
                    "slippage_bps": protocol.slippage_bps,
                    "min_matured_observations": protocol.min_matured_observations,
                    "definition_fingerprint_sha256": (
                        protocol.definition_fingerprint_sha256
                    ),
                },
                "baseline": {},
                "candidate_summary": {},
                "uplift_vs_baseline_pct_points": None,
                "observations": [],
            }
        ),
        encoding="utf-8",
    )

    latest_path, snapshot = collect_generic_report(
        fresh_report=fresh,
        bootstrap_artifact=bootstrap,
        latest_report=latest,
        history_dir=history,
    )
    assert latest_path.exists()
    assert snapshot.exists()
    assert latest.read_text(encoding="utf-8") == snapshot.read_text(
        encoding="utf-8"
    )
