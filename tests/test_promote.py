import json

import pytest

from bike_demand import promote


@pytest.fixture
def setup_dirs(tmp_path, monkeypatch):
    """Set up temporary candidate, accepted and previous directories."""
    candidate_dir = tmp_path / "artifacts" / "candidate"
    candidate_dir.mkdir(parents=True)
    accepted_dir = tmp_path / "models" / "accepted"
    accepted_dir.mkdir(parents=True)
    previous_dir = tmp_path / "models" / "previous"
    previous_dir.mkdir(parents=True)

    # Place a known accepted bundle so we can assert it stays unchanged
    (accepted_dir / "model.joblib").write_text("OLD_MODEL")
    (accepted_dir / "model-metadata.json").write_text(
        json.dumps({"model_version": "old"})
    )

    # Patch module-level paths to the temporary directories
    monkeypatch.setattr(promote, "CANDIDATE_DIR", candidate_dir)
    monkeypatch.setattr(promote, "ACCEPTED_DIR", accepted_dir)
    monkeypatch.setattr(promote, "PREVIOUS_DIR", previous_dir)

    return candidate_dir, accepted_dir, previous_dir


def test_promotion_fails_if_not_eligible(setup_dirs):
    """An ineligible decision record must leave the accepted bundle unchanged."""
    candidate_dir, accepted_dir, _ = setup_dirs

    (candidate_dir / "model.joblib").write_text("NEW_MODEL")
    (candidate_dir / "model-metadata.json").write_text(
        json.dumps({"model_version": "new"})
    )
    (candidate_dir / "decision_record.json").write_text(
        json.dumps({"outcome": "Rejected"})
    )

    result = promote.main()
    assert result == 1

    # Accepted bundle must not change
    assert (accepted_dir / "model.joblib").read_text() == "OLD_MODEL"
    assert (accepted_dir / "model-metadata.json").read_text() == (
        '{"model_version": "old"}'
    )


def test_promotion_fails_on_digest_mismatch(setup_dirs):
    """A digest mismatch must leave the accepted bundle unchanged."""
    candidate_dir, accepted_dir, _ = setup_dirs

    (candidate_dir / "model.joblib").write_text("NEW_MODEL")
    (candidate_dir / "model-metadata.json").write_text(
        json.dumps({"model_version": "new"})
    )
    (candidate_dir / "decision_record.json").write_text(
        json.dumps({"outcome": "Eligible", "candidate_sha256": "WRONG_DIGEST"})
    )

    result = promote.main()
    assert result == 1

    # Accepted bundle must not change
    assert (accepted_dir / "model.joblib").read_text() == "OLD_MODEL"
    assert (accepted_dir / "model-metadata.json").read_text() == (
        '{"model_version": "old"}'
    )
