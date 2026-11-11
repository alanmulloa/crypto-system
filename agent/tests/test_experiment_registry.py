import json

import pytest

from app.evaluation.experiment_registry import (
    ExperimentRegistry,
    ExperimentStatus,
    ResearchExperiment,
)
from app.evaluation.experiment_registry_cli import main as registry_cli_main


def experiment(**changes):
    values = {
        "id": "test-experiment",
        "symbol": "BTCUSDT",
        "strategy": "mean_reversion",
        "direction": "BUY",
        "feature": "volume_ratio_1h",
        "operator": "<=",
        "threshold": 0.8,
        "calibration_period": None,
        "validation_period": None,
        "freeze_at_ms": None,
        "outcome_hours": 24,
        "fee_bps": 10.0,
        "slippage_bps": 5.0,
        "status": ExperimentStatus.DRAFT,
        "decision": None,
        "artifact_path": "reports/research/test/",
    }
    values.update(changes)
    return ResearchExperiment(**values)


def test_registry_loads_valid_json(tmp_path):
    path = tmp_path / "registry.json"
    registry = ExperimentRegistry((experiment(),))
    path.write_text(registry.serialize(), encoding="utf-8")
    loaded = ExperimentRegistry.load(path)
    assert loaded == registry


def test_invalid_status_is_rejected():
    payload = experiment().to_dict()
    payload["status"] = "INVALID"
    with pytest.raises(ValueError, match="invalid experiment status"):
        ResearchExperiment.from_dict(payload)


def test_missing_required_field_is_rejected():
    payload = experiment().to_dict()
    del payload["symbol"]
    with pytest.raises(ValueError, match="missing experiment fields"):
        ResearchExperiment.from_dict(payload)


def test_xrp_5g_bootstrap_is_exact():
    registry = ExperimentRegistry.load(
        __import__("pathlib").Path("research/experiment-registry.json")
    )
    item = registry.get("phase5g-xrp-low-volume-1h")
    assert item.symbol == "XRPUSDT"
    assert item.strategy == "mean_reversion"
    assert item.direction == "BUY"
    assert item.feature == "volume_ratio_1h"
    assert item.operator == "<="
    assert item.threshold == 0.75
    assert item.freeze_at_ms == 1794348615195
    assert item.outcome_hours == 24
    assert item.fee_bps == 10.0
    assert item.slippage_bps == 5.0
    assert item.status is ExperimentStatus.PROSPECTIVE
    assert item.artifact_path == "reports/phase5g/"


def test_valid_status_transition():
    current = experiment(status=ExperimentStatus.DRAFT)
    updated = current.transition(ExperimentStatus.CALIBRATION)
    assert updated.status is ExperimentStatus.CALIBRATION


def test_invalid_status_transition():
    current = experiment(status=ExperimentStatus.DRAFT)
    with pytest.raises(ValueError, match="invalid experiment status transition"):
        current.transition(ExperimentStatus.PROSPECTIVE)


def test_frozen_experiment_definition_cannot_mutate():
    current = experiment(
        status=ExperimentStatus.FROZEN,
        freeze_at_ms=100,
    )
    with pytest.raises(ValueError, match="cannot mutate"):
        current.transition(
            ExperimentStatus.PROSPECTIVE,
            threshold=0.7,
        )


def test_prospective_experiment_definition_cannot_mutate():
    current = experiment(
        status=ExperimentStatus.PROSPECTIVE,
        freeze_at_ms=100,
    )
    with pytest.raises(ValueError, match="cannot mutate"):
        current.transition(
            ExperimentStatus.COMPLETE,
            fee_bps=12.0,
        )


def test_serialization_is_deterministic():
    first = experiment(id="b")
    second = experiment(id="a")
    registry = ExperimentRegistry((first, second))
    serialized = registry.serialize()
    assert serialized == registry.serialize()
    payload = json.loads(serialized)
    assert [item["id"] for item in payload["experiments"]] == ["a", "b"]


def test_cli_list_and_show(tmp_path, capsys):
    path = tmp_path / "registry.json"
    ExperimentRegistry((experiment(),)).save(path)

    assert registry_cli_main(["--registry", str(path), "list"]) == 0
    list_output = capsys.readouterr().out
    assert "test-experiment | DRAFT | BTCUSDT" in list_output

    assert (
        registry_cli_main(
            ["--registry", str(path), "--json", "show", "test-experiment"]
        )
        == 0
    )
    show_payload = json.loads(capsys.readouterr().out)
    assert show_payload["id"] == "test-experiment"
    assert show_payload["status"] == "DRAFT"


def test_add_experiment_rejects_duplicate_id():
    registry = ExperimentRegistry((experiment(),))
    with pytest.raises(ValueError, match="already exists"):
        registry.add_experiment(experiment())


def test_cli_register_creates_draft(tmp_path, capsys):
    path = tmp_path / "registry.json"
    ExperimentRegistry(tuple()).save(path)

    assert registry_cli_main(
        [
            "--registry",
            str(path),
            "register",
            "--id",
            "btc-low-volume",
            "--symbol",
            "btcusdt",
            "--strategy",
            "mean_reversion",
            "--direction",
            "buy",
            "--feature",
            "volume_ratio_1h",
            "--operator",
            "<=",
            "--threshold",
            "0.8",
            "--outcome-hours",
            "24",
            "--fee-bps",
            "10",
            "--slippage-bps",
            "5",
            "--artifact-path",
            "reports/research/btc-low-volume/",
        ]
    ) == 0
    assert "REGISTERED | btc-low-volume | DRAFT" in capsys.readouterr().out

    item = ExperimentRegistry.load(path).get("btc-low-volume")
    assert item.status is ExperimentStatus.DRAFT
    assert item.symbol == "BTCUSDT"
    assert item.direction == "BUY"
    assert item.freeze_at_ms is None
    assert item.decision is None


def test_cli_register_rejects_duplicate_id(tmp_path):
    path = tmp_path / "registry.json"
    ExperimentRegistry((experiment(id="dup"),)).save(path)

    args = [
        "--registry",
        str(path),
        "register",
        "--id",
        "dup",
        "--symbol",
        "BTCUSDT",
        "--strategy",
        "mean_reversion",
        "--direction",
        "BUY",
        "--feature",
        "volume_ratio_1h",
        "--operator",
        "<=",
        "--threshold",
        "0.8",
        "--outcome-hours",
        "24",
        "--fee-bps",
        "10",
        "--slippage-bps",
        "5",
        "--artifact-path",
        "reports/research/dup/",
    ]
    with pytest.raises(SystemExit, match="already exists"):
        registry_cli_main(args)


def test_cli_transition_draft_to_calibration(tmp_path, capsys):
    path = tmp_path / "registry.json"
    ExperimentRegistry((experiment(id="btc"),)).save(path)

    assert registry_cli_main(
        ["--registry", str(path), "transition", "btc", "CALIBRATION"]
    ) == 0
    assert "DRAFT -> CALIBRATION" in capsys.readouterr().out
    assert ExperimentRegistry.load(path).get("btc").status is ExperimentStatus.CALIBRATION


def test_cli_transition_to_frozen_requires_timestamp(tmp_path):
    path = tmp_path / "registry.json"
    item = experiment(id="btc", status=ExperimentStatus.VALIDATION)
    ExperimentRegistry((item,)).save(path)

    with pytest.raises(SystemExit, match="freeze-at-ms is required"):
        registry_cli_main(
            ["--registry", str(path), "transition", "btc", "FROZEN"]
        )


def test_cli_transition_to_frozen_sets_timestamp(tmp_path):
    path = tmp_path / "registry.json"
    item = experiment(id="btc", status=ExperimentStatus.VALIDATION)
    ExperimentRegistry((item,)).save(path)

    assert registry_cli_main(
        [
            "--registry",
            str(path),
            "transition",
            "btc",
            "FROZEN",
            "--freeze-at-ms",
            "123456",
        ]
    ) == 0
    frozen = ExperimentRegistry.load(path).get("btc")
    assert frozen.status is ExperimentStatus.FROZEN
    assert frozen.freeze_at_ms == 123456


def test_cli_transition_rejects_invalid_jump(tmp_path):
    path = tmp_path / "registry.json"
    ExperimentRegistry((experiment(id="btc"),)).save(path)

    with pytest.raises(SystemExit, match="invalid experiment status transition"):
        registry_cli_main(
            ["--registry", str(path), "transition", "btc", "VALIDATION"]
        )


def test_cli_transition_cannot_mutate_xrp_prospective(tmp_path):
    source = ExperimentRegistry.load(
        __import__("pathlib").Path("research/experiment-registry.json")
    )
    path = tmp_path / "registry.json"
    source.save(path)

    with pytest.raises(SystemExit, match="invalid experiment status transition"):
        registry_cli_main(
            [
                "--registry",
                str(path),
                "transition",
                "phase5g-xrp-low-volume-1h",
                "CALIBRATION",
            ]
        )
