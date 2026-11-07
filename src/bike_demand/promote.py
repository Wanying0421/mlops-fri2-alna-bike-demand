"""Manual promotion of a candidate model to the accepted bundle."""

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

from bike_demand.bundles import verify_candidate_bundle

CANDIDATE_DIR = Path("artifacts")
MODELS_DIR = Path("models")
CURRENT_POINTER = MODELS_DIR / "current_version.txt"
PREVIOUS_POINTER = MODELS_DIR / "previous_version.txt"
REQUIRED_FILES = ("model.joblib", "model-metadata.json")


def _sha256(path: Path) -> str:
    """Compute the SHA-256 digest of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_eligibility_and_bundle(candidate_dir: Path) -> None:
    """Verify eligibility and the complete bundle via the shared manifest."""
    decision_file = candidate_dir / "decision_record.json"
    if not decision_file.exists():
        raise ValueError("Missing decision_record.json")

    decision = json.loads(decision_file.read_text())
    if decision.get("outcome") != "Eligible":
        raise ValueError(f"Not eligible: {decision.get('outcome')}")

    candidate_id = decision.get("candidate_id")
    expected_digest = decision.get("bundle_sha256")
    if not candidate_id or not expected_digest:
        raise ValueError("Decision missing candidate_id or bundle_sha256")

    # Use the shared verify_candidate_bundle reader on the candidate
    verify_candidate_bundle(candidate_dir, expected_digest)


def _read_pointer(pointer: Path) -> str | None:
    """Read a version pointer if it exists."""
    return pointer.read_text().strip() if pointer.exists() else None


def _write_pointers(current: str | None, previous: str | None) -> None:
    """Write both pointers only after staging succeeds. Neither is touched on failure."""
    with tempfile.TemporaryDirectory(dir=MODELS_DIR) as temp_dir:
        tmp_current = Path(temp_dir) / "current.txt"
        tmp_previous = Path(temp_dir) / "previous.txt"

        if current:
            tmp_current.write_text(current)
        if previous:
            tmp_previous.write_text(previous)

        # Move previous first, then current
        if previous:
            shutil.move(str(tmp_previous), PREVIOUS_POINTER)
        if current:
            shutil.move(str(tmp_current), CURRENT_POINTER)


def _atomic_promote(candidate_dir: Path) -> None:
    """Stage, verify, and switch. Version directories are immutable."""
    model_hash = _sha256(candidate_dir / "model.joblib")[:8]
    new_version_name = f"version-{model_hash}"
    new_version_path = MODELS_DIR / new_version_name

    with tempfile.TemporaryDirectory(dir=MODELS_DIR) as temp_dir:
        staging = Path(temp_dir)
        for name in REQUIRED_FILES:
            shutil.copy2(candidate_dir / name, staging / name)

        # Re-verify the staged bundle with the shared reader
        decision_file = candidate_dir / "decision_record.json"
        decision = json.loads(decision_file.read_text())
        verify_candidate_bundle(staging, decision["bundle_sha256"])

        if new_version_path.exists():
            shutil.rmtree(new_version_path)
        shutil.move(str(staging), str(new_version_path))

    current_version = _read_pointer(CURRENT_POINTER)
    _write_pointers(current=new_version_name, previous=current_version)


def main() -> int:
    """Run the promotion pipeline."""
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
