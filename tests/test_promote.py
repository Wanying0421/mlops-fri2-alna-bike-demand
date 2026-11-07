import hashlib
import json
from pathlib import Path

import pytest

from bike_demand import promote


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def valid_setup(tmp_path, monkeypatch):
    candidate_dir = tmp_path / "candidate"
    candidate_dir.mkdir(parents=True)
    models_dir = tmp_path / "models"
    models_dir.mkdir(parents=True)

    # Create dummy files for the bundle
    for name in promote.BUNDLE_FILES:
        (candidate_dir / name).write_text(f"dummy_{name}")
    (candidate_dir / "bundle.json").write_text('{"dummy": "bundle"}')
    (candidate_dir / "decision_record.json").write_text(
        json.dumps(
            {
                "outcome": "Eligible",
                "candidate_id": "cand-123",
                "bundle_sha256": "dummy",
            }
        )
    )

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

    # Mock the verifier to always pass for this test
    monkeypatch.setattr(
        promote, "verify_candidate_bundle", lambda *args, **kwargs: None
    )

    return candidate_dir, models_dir


def test_successful_promotion_updates_versions(valid_setup):
    candidate_dir, models_dir = valid_setup
    result = promote.main()
    assert result == 0

    versions = json.loads((models_dir / "versions.json").read_text())
    assert versions["previous"] == "version-old"
    assert versions["current"].startswith("version-")


def test_not_eligible_blocks_promotion(valid_setup):
    candidate_dir, models_dir = valid_setup
    (candidate_dir / "decision_record.json").write_text(
        json.dumps(
            {
                "outcome": "Rejected",
                "candidate_id": "cand-123",
                "bundle_sha256": "dummy",
            }
        )
    )
    result = promote.main()
    assert result == 1
    versions = json.loads((models_dir / "versions.json").read_text())
    assert versions["current"] == "version-old"


def test_interrupted_staging_copy_leaves_state_unchanged(valid_setup, monkeypatch):
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
