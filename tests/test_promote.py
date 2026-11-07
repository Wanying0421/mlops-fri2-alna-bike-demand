import hashlib
import json
from pathlib import Path

import pytest

from bike_demand import promote


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def setup_dirs(tmp_path, monkeypatch):
    """Set up temporary directories and a valid candidate."""
    candidate_dir = tmp_path / "candidate"
    candidate_dir.mkdir(parents=True)
    models_dir = tmp_path / "models"
    models_dir.mkdir(parents=True)

    # Créer un faux candidat valide
    (candidate_dir / "model.joblib").write_text("NEW_MODEL")
    (candidate_dir / "model-metadata.json").write_text(
        json.dumps({"model_version": "new"})
    )

    bundle = {
        "model.joblib": _sha256(candidate_dir / "model.joblib"),
        "model-metadata.json": _sha256(candidate_dir / "model-metadata.json"),
    }
    (candidate_dir / "bundle.json").write_text(json.dumps(bundle))
    (candidate_dir / "decision_record.json").write_text(
        json.dumps(
            {
                "outcome": "Eligible",
                "bundle_sha256": _sha256(candidate_dir / "bundle.json"),
            }
        )
    )

    # Simuler un ancien accepted
    (models_dir / "version-old").mkdir()
    (models_dir / "version-old" / "model.joblib").write_text("OLD_MODEL")
    (models_dir / "accepted_pointer.txt").write_text("version-old")

    monkeypatch.setattr(promote, "CANDIDATE_DIR", candidate_dir)
    monkeypatch.setattr(promote, "MODELS_DIR", models_dir)
    monkeypatch.setattr(
        promote, "ACCEPTED_POINTER", models_dir / "accepted_pointer.txt"
    )

    return candidate_dir, models_dir


def test_promotion_fails_if_metadata_is_modified(setup_dirs):
    """Changing metadata after the decision must fail the promotion."""
    candidate_dir, models_dir = setup_dirs
    # Modifier le fichier de métadonnées après la décision
    (candidate_dir / "model-metadata.json").write_text(
        json.dumps({"model_version": "HACKED"})
    )

    result = promote.main()
    assert result == 1
    # L'état accepted n'a pas changé
    assert (models_dir / "accepted_pointer.txt").read_text() == "version-old"
    assert (models_dir / "version-old" / "model.joblib").read_text() == "OLD_MODEL"


def test_promotion_fails_if_staging_is_interrupted(setup_dirs, monkeypatch):
    """An interrupted copy must leave accepted and previous untouched."""
    candidate_dir, models_dir = setup_dirs

    # Simuler une erreur pendant la copie
    def mock_copy(*args, **kwargs):
        raise OSError("Simulated copy failure")

    monkeypatch.setattr("shutil.copy2", mock_copy)

    result = promote.main()
    assert result == 1
    assert (models_dir / "accepted_pointer.txt").read_text() == "version-old"


def test_promotion_fails_if_switch_is_interrupted(setup_dirs, monkeypatch):
    """An interrupted pointer update must leave accepted unchanged."""
    candidate_dir, models_dir = setup_dirs

    # Simuler une erreur au moment du switch final
    def mock_move(*args, **kwargs):
        raise OSError("Simulated move failure")

    monkeypatch.setattr("shutil.move", mock_move)

    result = promote.main()
    assert result == 1
    assert (models_dir / "accepted_pointer.txt").read_text() == "version-old"
