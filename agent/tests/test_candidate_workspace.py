import json
from pathlib import Path

import pytest

from app.evaluation.candidate_workspace import (
    CandidateResearchWorkspace,
    initialize_workspace,
)
from app.evaluation.candidate_workspace_cli import main as workspace_cli_main
from app.evaluation.experiment_registry import (
    ExperimentRegistry,
    ExperimentStatus,
    ResearchExperiment,
)


def experiment(**changes):
    values = {
        "id": "btc-draft",
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
        "artifact_path": "reports/research/btc-draft/",
    }
    values.update(changes)
    return ResearchExperiment(**values)


def write_registry(path: Path, item: ResearchExperiment) -> None:
    ExperimentRegistry((item,)).save(path)


def test_workspace_initializes_for_draft(tmp_path):
    item = experiment()
    manifest = initialize_workspace(
        experiment=item,
        workspace_root=tmp_path / "workspaces",
    )
    workspace = CandidateResearchWorkspace.load(manifest)
    assert workspace.experiment_id == item.id
    assert workspace.research_only is True
    assert workspace.phase6_blocked is True
    assert (manifest.parent / "artifacts").is_dir()
    assert (manifest.parent / "notes").is_dir()


@pytest.mark.parametrize(
    "status",
    [
        ExperimentStatus.FROZEN,
        ExperimentStatus.PROSPECTIVE,
        ExperimentStatus.COMPLETE,
        ExperimentStatus.REJECTED,
    ],
)
def test_workspace_rejects_non_research_statuses(status, tmp_path):
    item = experiment(
        status=status,
        freeze_at_ms=100 if status in {
            ExperimentStatus.FROZEN,
            ExperimentStatus.PROSPECTIVE,
            ExperimentStatus.COMPLETE,
        } else None,
    )
    with pytest.raises(ValueError, match="workspace not allowed"):
        initialize_workspace(
            experiment=item,
            workspace_root=tmp_path / "workspaces",
        )


def test_existing_workspace_init_is_idempotent(tmp_path):
    item = experiment()
    root = tmp_path / "workspaces"
    first = initialize_workspace(experiment=item, workspace_root=root)
    second = initialize_workspace(experiment=item, workspace_root=root)
    assert first == second


def test_workspace_detects_definition_drift(tmp_path):
    item = experiment()
    manifest = initialize_workspace(
        experiment=item,
        workspace_root=tmp_path / "workspaces",
    )
    workspace = CandidateResearchWorkspace.load(manifest)
    changed = experiment(threshold=0.7)
    with pytest.raises(ValueError, match="definition diverged"):
        workspace.validate_against(changed)


def test_workspace_allows_lifecycle_progress_with_same_definition(tmp_path):
    item = experiment(status=ExperimentStatus.DRAFT)
    manifest = initialize_workspace(
        experiment=item,
        workspace_root=tmp_path / "workspaces",
    )
    workspace = CandidateResearchWorkspace.load(manifest)
    calibration = experiment(status=ExperimentStatus.CALIBRATION)
    workspace.validate_against(calibration)


def test_workspace_manifest_serialization_is_deterministic():
    workspace = CandidateResearchWorkspace.from_experiment(experiment())
    assert workspace.serialize() == workspace.serialize()
    payload = json.loads(workspace.serialize())
    assert payload["workspace_kind"] == "candidate-research"
    assert payload["phase6_blocked"] is True


def test_cli_init_validate_and_show(tmp_path, capsys):
    registry_path = tmp_path / "registry.json"
    workspace_root = tmp_path / "workspaces"
    write_registry(registry_path, experiment())

    common = [
        "--registry",
        str(registry_path),
        "--workspace-root",
        str(workspace_root),
    ]

    assert workspace_cli_main([*common, "init", "btc-draft"]) == 0
    assert "workspace.json" in capsys.readouterr().out

    assert workspace_cli_main([*common, "validate", "btc-draft"]) == 0
    assert "VALID | btc-draft | DRAFT" in capsys.readouterr().out

    assert workspace_cli_main([*common, "--json", "show", "btc-draft"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["experiment_id"] == "btc-draft"
    assert payload["research_only"] is True


def test_xrp_5g_prospective_registry_entry_cannot_open_workspace(tmp_path):
    registry = ExperimentRegistry.load(Path("research/experiment-registry.json"))
    xrp = registry.get("phase5g-xrp-low-volume-1h")
    assert xrp.status is ExperimentStatus.PROSPECTIVE
    with pytest.raises(ValueError, match="PROSPECTIVE"):
        initialize_workspace(
            experiment=xrp,
            workspace_root=tmp_path / "workspaces",
        )
