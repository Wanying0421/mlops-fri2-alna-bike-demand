"""Tests for the model promotion script."""

import hashlib
import json
from pathlib import Path

import pytest

from bike_demand import promote


def _sha256(path: Path) -> str:
    """Compute the SHA-256 digest of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def setup_dirs(tmp_path, monkeypatch):
    """Create temporary candidate and models directories."""
    candidate_dir = tmp_path / "candidate"
    candidate_dir.mkdir(parents=True)
    models_dir = tmp_path / "models"
    models_dir.mkdir(parents=True)

    # Build a valid candidate bundle
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

    # Simulate existing accepted and previous versions
    (models_dir / "version-old").mkdir()
    (models_dir / "version-old" / "model.joblib").write_text("OLD_MODEL")
    (models_dir / "version-old" / "model-metadata.json").write_text(
        '{"model_version": "old"}'
    )
    (models_dir / "current_version.txt").write_text("version-old")
    (models_dir / "previous_version.txt").write_text("version-older")

    # Patch module-level paths
    monkeypatch.setattr(promote, "CANDIDATE_DIR", candidate_dir)
    monkeypatch.setattr(promote, "MODELS_DIR", models_dir)
    monkeypatch.setattr(promote, "CURRENT_POINTER", models_dir / "current_version.txt")
    monkeypatch.setattr(
        promote, "PREVIOUS_POINTER", models_dir / "previous_version.txt"
    )

    return candidate_dir, models_dir


def test_manifest_rejects_invalid_candidate_id(setup_dirs):
    """A wrong candidate ID in the bundle must block promotion."""
    candidate_dir, models_dir = setup_dirs
    bundle = json.loads((candidate_dir / "bundle.json").read_text())
    bundle["candidate_id"] = "WRONG_ID"
    (candidate_dir / "bundle.json").write_text(json.dumps(bundle))

    result = promote.main()
    assert result == 1
    assert (models_dir / "current_version.txt").read_text() == "version-old"


def test_metadata_tampering_rejected(setup_dirs):
    """Modifying metadata after the bundle must fail because the digest no longer matches."""
    candidate_dir, models_dir = setup_dirs
    (candidate_dir / "model-metadata.json").write_text(
        json.dumps({"model_version": "HACKED"})
    )

    result = promote.main()
    assert result == 1
    assert (models_dir / "current_version.txt").read_text() == "version-old"


def test_interrupted_staging_copy_leaves_state_unchanged(setup_dirs, monkeypatch):
    """A copy failure during staging must leave both references untouched."""
    candidate_dir, models_dir = setup_dirs

    def mock_copy(*args, **kwargs):
        raise OSError("Simulated copy failure")

    monkeypatch.setattr(promote.shutil, "copy2", mock_copy)

    result = promote.main()
    assert result == 1
    assert (models_dir / "current_version.txt").read_text() == "version-old"
    assert (models_dir / "previous_version.txt").read_text() == "version-older"


def test_pointer_switch_failure_leaves_previous_intact(setup_dirs, monkeypatch):
    """A crash on the current pointer move must leave both references intact."""
    candidate_dir, models_dir = setup_dirs

    original_move = promote.shutil.move

    def mock_move(src, dst):
        if "current.txt" in str(src):
            raise OSError("Simulated pointer crash")
        return original_move(src, dst)

    monkeypatch.setattr(promote.shutil, "move", mock_move)

    result = promote.main()
    assert result == 1
    assert (models_dir / "current_version.txt").read_text() == "version-old"
    assert (models_dir / "previous_version.txt").read_text() == "version-older"
