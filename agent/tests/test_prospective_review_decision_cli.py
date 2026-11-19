import json

from app.evaluation.prospective_bootstrap import (
    GenericProspectiveProtocol,
    protocol_to_dict,
)
from app.evaluation.prospective_review_decision_cli import main


def test_cli_writes_review_and_decision(tmp_path, capsys):
    protocol = GenericProspectiveProtocol(
        experiment_id="candidate",
        symbol="BTCUSDT",
        strategy="mean_reversion",
        direction="BUY",
        feature="volume_ratio_1h",
        operator="<=",
        threshold=0.75,
        frozen_at_ms=1000,
        outcome_hours=24,
        fee_bps=10.0,
        slippage_bps=5.0,
        min_matured_observations=20,
        definition_fingerprint_sha256="a" * 64,
    )
    bootstrap = tmp_path / "bootstrap.json"
    source = tmp_path / "latest.json"
    review = tmp_path / "review.json"
    decision = tmp_path / "decision.json"

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
    source.write_text(
        json.dumps(
            {
                "metadata": {
                    "phase": "5H.10-prospective",
                    "created_at": "now",
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
                    "min_matured_observations": 20,
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

    assert main(
        [
            "--input", str(source),
            "--bootstrap", str(bootstrap),
            "--review-output", str(review),
            "--decision-output", str(decision),
        ]
    ) == 0

    output = json.loads(decision.read_text(encoding="utf-8"))
    assert output["decision"] == "NOT_READY"
    assert output["phase6_eligible"] is False
    assert output["phase6_blocked"] is True
    assert "WAITING_FOR_CANDIDATE_SIGNAL" in capsys.readouterr().out
