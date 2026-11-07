import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

CANDIDATE_DIR = Path("artifacts/candidate")
MODELS_DIR = Path("models")
ACCEPTED_POINTER = MODELS_DIR / "accepted_pointer.txt"
REQUIRED_FILES = ("model.joblib", "model-metadata.json")


def _calculate_sha256(path: Path) -> str:
    """Compute the SHA-256 digest of a file."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _check_eligibility_and_bundle(candidate_dir: Path) -> Path:
    """Verify eligibility and the complete bundle digest."""
    decision_file = candidate_dir / "decision_record.json"
    bundle_file = candidate_dir / "bundle.json"

    if not decision_file.exists() or not bundle_file.exists():
        raise ValueError("Missing decision_record.json or bundle.json")

    decision = json.loads(decision_file.read_text())
    if decision.get("outcome") != "Eligible":
        raise ValueError(f"Candidate is not eligible: {decision.get('outcome')}")

    # On vérifie que le bundle entier correspond au SHA-256 de la décision
    expected_digest = decision.get("bundle_sha256")
    if not expected_digest:
        raise ValueError("Decision record missing bundle_sha256")

    actual_digest = _calculate_sha256(bundle_file)
    if actual_digest != expected_digest:
        raise ValueError("Bundle SHA-256 digest mismatch")

    # On vérifie que le bundle.json correspond bien aux fichiers présents
    bundle = json.loads(bundle_file.read_text())
    for name, file_digest in bundle.items():
        path = candidate_dir / name
        if not path.exists():
            raise FileNotFoundError(f"Missing file in bundle: {name}")
        if _calculate_sha256(path) != file_digest:
            raise ValueError(f"File digest mismatch for {name}")

    return candidate_dir


def _get_current_accepted() -> str | None:
    if ACCEPTED_POINTER.exists():
        return ACCEPTED_POINTER.read_text().strip()
    return None


def _set_pointer(version_dir_name: str) -> None:
    # Écriture atomique du pointeur
    with tempfile.NamedTemporaryFile("w", dir=MODELS_DIR, delete=False) as f:
        f.write(version_dir_name)
        temp_path = f.name
    shutil.move(temp_path, ACCEPTED_POINTER)


def _atomic_promote(candidate_dir: Path) -> None:
    current_version = _get_current_accepted()
    new_version_name = (
        f"version-{_calculate_sha256(candidate_dir / 'model.joblib')[:8]}"
    )
    new_version_path = MODELS_DIR / new_version_name

    # 1. Préparer et vérifier dans le staging (on copie dans un dossier version-XXX)
    with tempfile.TemporaryDirectory(dir=MODELS_DIR) as temp_dir:
        staging = Path(temp_dir)
        for name in REQUIRED_FILES:
            shutil.copy2(candidate_dir / name, staging / name)

        # Vérification
        for name in REQUIRED_FILES:
            if not (staging / name).exists():
                raise ValueError(f"Staging failed for {name}")

        # 2. Déplacer le staging vers son dossier final
        if new_version_path.exists():
            shutil.rmtree(new_version_path)
        shutil.move(str(staging), str(new_version_path))

    # 3. Sauvegarder l'ancien dans previous (si on a un ancien pointeur)
    if current_version:
        previous_path = MODELS_DIR / "previous"
        if previous_path.exists():
            shutil.rmtree(previous_path)
        shutil.copytree(MODELS_DIR / current_version, previous_path)

    # 4. Switch atomique : on met juste à jour le pointeur (fichier texte)
    _set_pointer(new_version_name)


def main() -> int:
    try:
        _check_eligibility_and_bundle(CANDIDATE_DIR)
        _atomic_promote(CANDIDATE_DIR)
    except Exception as error:
        print(f"Promotion failed: {error}", file=sys.stderr)
        return 1

    print("Promotion complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
