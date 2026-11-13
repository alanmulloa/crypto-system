import json

import pytest

from app.evaluation.candidate_discovery import (
    discover_from_phase5f1_payload,
    discover_from_symbol_report,
    proposal_id,
)
from app.evaluation.candidate_discovery_cli import main as discovery_cli_main


def evidence(
    *,
    feature="volume_ratio_1h",
    bucket="<=0.75",
    cal_obs=30,
    val_obs=25,
    cal_return=0.4,
    val_return=0.3,
    cal_uplift=0.5,
    val_uplift=0.4,
    sufficient=True,
    positive_return=True,
    positive_uplift=True,
):
    return {
        "feature": feature,
        "bucket": bucket,
        "calibration_observations": cal_obs,
        "validation_observations": val_obs,
        "calibration_average_return_pct": cal_return,
        "validation_average_return_pct": val_return,
        "calibration_uplift_pct_points": cal_uplift,
        "validation_uplift_pct_points": val_uplift,
        "stable_positive_uplift": positive_uplift,
        "stable_positive_return": positive_return,
        "sufficient_sample_both": sufficient,
    }


def report(*rows, symbol="BTCUSDT"):
    return {
        "symbol": symbol,
        "strategy": "mean_reversion",
        "outcome_hours": 24,
        "cross_segment_evidence": list(rows),
    }


def payload(*reports):
    return {
        "metadata": {
            "phase": "5F.1",
            "research_only": True,
        },
        "results": list(reports),
        "pooled": {},
    }


def test_supported_stable_bucket_becomes_proposal():
    proposals = discover_from_symbol_report(report(evidence()))
    assert len(proposals) == 1
    item = proposals[0]
    assert item.symbol == "BTCUSDT"
    assert item.feature == "volume_ratio_1h"
    assert item.operator == "<="
    assert item.threshold == 0.75
    assert item.recommendation == "RESEARCH_CANDIDATE"
    assert item.auto_register is False
    assert item.auto_freeze is False


def test_middle_range_bucket_is_not_promoted_to_rule():
    proposals = discover_from_symbol_report(
        report(evidence(bucket="0.75-1.5"))
    )
    assert proposals == ()


@pytest.mark.parametrize(
    "field,value",
    [
        ("sufficient", False),
        ("positive_return", False),
        ("positive_uplift", False),
    ],
)
def test_candidate_requires_all_research_screens(field, value):
    kwargs = {field: value}
    proposals = discover_from_symbol_report(report(evidence(**kwargs)))
    assert proposals == ()


def test_missing_metric_is_rejected():
    row = evidence()
    row["validation_uplift_pct_points"] = None
    assert discover_from_symbol_report(report(row)) == ()


def test_categorical_structure_rule_is_supported():
    proposals = discover_from_symbol_report(
        report(
            evidence(
                feature="structure_4h",
                bucket="lower_highs_lower_lows",
            ),
            symbol="ETHUSDT",
        )
    )
    assert len(proposals) == 1
    assert proposals[0].operator == "=="
    assert proposals[0].threshold == "lower_highs_lower_lows"


def test_discovery_ranking_uses_validation_not_oos():
    low = evidence(val_uplift=0.2, val_return=0.2)
    high = evidence(
        feature="rsi_1h",
        bucket="<=25",
        val_uplift=0.7,
        val_return=0.5,
    )
    proposals = discover_from_symbol_report(report(low, high))
    assert [item.feature for item in proposals] == ["rsi_1h", "volume_ratio_1h"]


def test_phase5f1_artifact_required():
    with pytest.raises(ValueError, match="Phase 5F.1"):
        discover_from_phase5f1_payload(
            {"metadata": {"phase": "5F.2", "research_only": True}, "results": []}
        )


def test_research_only_artifact_required():
    with pytest.raises(ValueError, match="research_only"):
        discover_from_phase5f1_payload(
            {"metadata": {"phase": "5F.1", "research_only": False}, "results": []}
        )


def test_proposal_id_is_deterministic():
    assert proposal_id(
        symbol="BTCUSDT",
        feature="volume_ratio_1h",
        operator="<=",
        threshold=0.75,
    ) == "btcusdt-volume_ratio_1h-lte-0p75"


def test_cli_writes_proposals_without_registry_side_effects(tmp_path, capsys):
    source = tmp_path / "phase5f1.json"
    output = tmp_path / "discovery.json"
    source.write_text(
        json.dumps(payload(report(evidence()))),
        encoding="utf-8",
    )

    assert discovery_cli_main(
        ["--input", str(source), "--output", str(output)]
    ) == 0
    assert "1 proposals" in capsys.readouterr().out

    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["metadata"]["auto_register"] is False
    assert result["metadata"]["auto_freeze"] is False
    assert result["metadata"]["phase6_blocked"] is True
    assert result["proposal_count"] == 1
    assert result["proposals"][0]["symbol"] == "BTCUSDT"
