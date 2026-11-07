import hashlib
import json
from pathlib import Path

import pytest

from bike_demand import promote


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def valid_setup(tmp_path, monkeypatch):
    """Create a valid candidate bundle and existing versions.json."""
    candidate_dir = tmp_path / "candidate"
    candidate_dir.mkdir(parents=True)
    models_dir = tmp_path / "models"
    models_dir.mkdir(parents=True)

    (candidate_dir / "model.joblib").write_text("NEW_MODEL")
    (candidate_dir / "model-metadata.json").write_text(
        json.dumps({"model_version": "new"})
    )

    bundle = {
        "candidate_id": "cand-123",
        "files": {
            "model.joblib": _sha256(candidate_dir / "model.joblib"),
            "model-metadata.json": _sha256(candidate_dir / "model-metadata.json"),
        },
    }
    (candidate_dir / "bundle.json").write_text(json.dumps(bundle))

    decision = {
        "outcome": "Eligible",
        "candidate_id": "cand-123",
        "bundle_sha256": _sha256(candidate_dir / "bundle.json"),
    }
    (candidate_dir / "decision_record.json").write_text(json.dumps(decision))

    (models_dir / "version-old").mkdir()
    (models_dir / "version-old" / "model.joblib").write_text("OLD_MODEL")
    (models_dir / "version-old" / "model-metadata.json").write_text(
        '{"model_version": "old"}'
    )
    (models_dir / "versions.json").write_text(
        json.dumps({"current": "version-old", "previous": "version-older"})
    )

    monkeypatch.setattr(promote, "CANDIDATE_DIR", candidate_dir)
    monkeypatch.setattr(promote, "MODELS_DIR", models_dir)
    monkeypatch.setattr(promote, "VERSIONS_FILE", models_dir / "versions.json")

    return candidate_dir, models_dir


def test_successful_promotion_updates_versions(valid_setup):
    """A valid bundle must promote and update versions.json."""
    candidate_dir, models_dir = valid_setup
    result = promote.main()
    assert result == 0

    versions = json.loads((models_dir / "versions.json").read_text())
    assert versions["previous"] == "version-old"
    assert versions["current"].startswith("version-")


def test_manifest_rejects_invalid_candidate_id(valid_setup):
    """A wrong candidate ID must block promotion."""
    candidate_dir, models_dir = valid_setup
    bundle = json.loads((candidate_dir / "bundle.json").read_text())
    bundle["candidate_id"] = "WRONG_ID"
    (candidate_dir / "bundle.json").write_text(json.dumps(bundle))

    result = promote.main()
    assert result == 1
    versions = json.loads((models_dir / "versions.json").read_text())
    assert versions["current"] == "version-old"


def test_metadata_tampering_rejected(valid_setup):
    """Modifying metadata after the bundle must fail."""
    candidate_dir, models_dir = valid_setup
    (candidate_dir / "model-metadata.json").write_text(
        json.dumps({"model_version": "HACKED"})
    )

    result = promote.main()
    assert result == 1
    versions = json.loads((models_dir / "versions.json").read_text())
    assert versions["current"] == "version-old"


def test_interrupted_staging_copy_leaves_state_unchanged(valid_setup, monkeypatch):
    """A copy failure during staging must leave versions.json untouched."""
    candidate_dir, models_dir = valid_setup

    def mock_copy(*args, **kwargs):
        raise OSError("Simulated copy failure")

    monkeypatch.setattr(promote.shutil, "copy2", mock_copy)

    result = promote.main()
    assert result == 1
    versions = json.loads((models_dir / "versions.json").read_text())
    assert versions["current"] == "version-old"
    assert versions["previous"] == "version-older"


def test_pointer_switch_failure_leaves_both_references_intact(valid_setup, monkeypatch):
    """A crash during the atomic versions.json replacement must leave both references intact."""
    candidate_dir, models_dir = valid_setup

    original_replace = promote.os.replace

    def mock_replace(src, dst):
        if "versions.json" in str(dst):
            raise OSError("Simulated pointer crash")
        return original_replace(src, dst)

    monkeypatch.setattr(promote.os, "replace", mock_replace)

    result = promote.main()
    assert result == 1
    versions = json.loads((models_dir / "versions.json").read_text())
    assert versions["current"] == "version-old"
    assert versions["previous"] == "version-older"
