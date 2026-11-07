import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

# Directory holding the candidate bundle and its decision record
CANDIDATE_DIR = Path("artifacts/candidate")
# Directory holding the currently accepted bundle
ACCEPTED_DIR = Path("models/accepted")
# Directory holding the previous accepted bundle (for rollback)
PREVIOUS_DIR = Path("models/previous")
# Files that make up a complete model bundle
REQUIRED_FILES = ("model.joblib", "model-metadata.json")


def _calculate_sha256(path: Path) -> str:
    """Compute the SHA-256 digest of a file."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _check_eligibility(candidate_dir: Path) -> None:
    """Verify that the candidate is eligible and matches its recorded digest."""
    decision_file = candidate_dir / "decision_record.json"
    if not decision_file.exists():
        raise ValueError("Missing decision_record.json")

    decision = json.loads(decision_file.read_text())
    if decision.get("outcome") != "Eligible":
        raise ValueError(f"Candidate is not eligible: {decision.get('outcome')}")

    expected_digest = decision.get("candidate_sha256")
    if not expected_digest:
        raise ValueError("Decision record missing candidate_sha256")

    model_path = candidate_dir / "model.joblib"
    if not model_path.exists():
        raise FileNotFoundError(f"Candidate model missing: {model_path}")

    actual_digest = _calculate_sha256(model_path)
    if actual_digest != expected_digest:
        raise ValueError("SHA-256 digest mismatch")


def _backup_accepted() -> None:
    """Copy the current accepted bundle to the previous directory."""
    if not ACCEPTED_DIR.exists() or not any(ACCEPTED_DIR.iterdir()):
        print("No accepted bundle to back up.")
        return
    PREVIOUS_DIR.mkdir(parents=True, exist_ok=True)
    # Clear the previous directory
    for item in PREVIOUS_DIR.iterdir():
        if item.is_file():
            item.unlink()
    for name in REQUIRED_FILES:
        src = ACCEPTED_DIR / name
        if src.exists():
            shutil.copy2(src, PREVIOUS_DIR / name)
    print(f"Backed up accepted bundle to {PREVIOUS_DIR}")


def _atomic_promote(candidate_dir: Path) -> None:
    """Stage the candidate fully, then atomically replace the accepted bundle."""
    # Create a staging directory in the same parent for atomic move
    with tempfile.TemporaryDirectory(dir="models") as temp_dir:
        staging = Path(temp_dir)

        # Copy all required files into staging
        for name in REQUIRED_FILES:
            shutil.copy2(candidate_dir / name, staging / name)

        # Verify that the staging bundle is complete
        for name in REQUIRED_FILES:
            if not (staging / name).exists():
                raise ValueError(f"Staging failed for {name}")

        # Atomic switch: remove old accepted and replace with staging
        if ACCEPTED_DIR.exists():
            shutil.rmtree(ACCEPTED_DIR)
        shutil.move(str(staging), str(ACCEPTED_DIR))


def main() -> int:
    """Run the promotion pipeline."""
    try:
        _check_eligibility(CANDIDATE_DIR)
        _backup_accepted()
        _atomic_promote(CANDIDATE_DIR)
    except Exception as error:
        print(f"Promotion failed: {error}", file=sys.stderr)
        return 1

    metadata = json.loads((ACCEPTED_DIR / "model-metadata.json").read_text())
    print("Promotion complete.")
    print(f"Accepted model_version: {metadata.get('model_version')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
