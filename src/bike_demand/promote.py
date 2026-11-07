import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

CANDIDATE_DIR = Path("artifacts/candidate")
MODELS_DIR = Path("models")
CURRENT_POINTER = MODELS_DIR / "current_version.txt"
PREVIOUS_POINTER = MODELS_DIR / "previous_version.txt"
REQUIRED_FILES = ("model.joblib", "model-metadata.json")


def _sha256(path: Path) -> str:
    """Compute the SHA-256 digest of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_eligibility_and_bundle(candidate_dir: Path) -> None:
    """Verify eligibility and that the complete bundle matches its manifest."""
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

    # 1. Verify the manifest digest matches the decision
    bundle_file = candidate_dir / "bundle.json"
    if not bundle_file.exists():
        raise ValueError("Missing bundle.json")

    if _sha256(bundle_file) != expected_digest:
        raise ValueError("Bundle digest mismatch")

    # 2. Verify the bundle contains the right candidate ID and file digests
    bundle = json.loads(bundle_file.read_text())
    if bundle.get("candidate_id") != candidate_id:
        raise ValueError("Candidate ID mismatch in bundle.json")

    for name, expected_file_hash in bundle.get("files", {}).items():
        path = candidate_dir / name
        if not path.exists():
            raise FileNotFoundError(f"Missing file in bundle: {name}")
        if _sha256(path) != expected_file_hash:
            raise ValueError(f"File digest mismatch for {name}")


def _read_pointer(pointer: Path) -> str | None:
    """Read a version pointer if it exists."""
    return pointer.read_text().strip() if pointer.exists() else None


def _write_pointers(current: str | None, previous: str | None) -> None:
    """Atomically write both current and previous pointers."""
    with tempfile.TemporaryDirectory(dir=MODELS_DIR) as temp_dir:
        tmp_current = Path(temp_dir) / "current.txt"
        tmp_previous = Path(temp_dir) / "previous.txt"

        if current:
            tmp_current.write_text(current)
        if previous:
            tmp_previous.write_text(previous)

        # Move each pointer into place as atomically as possible
        if current:
            shutil.move(str(tmp_current), CURRENT_POINTER)
        if previous:
            shutil.move(str(tmp_previous), PREVIOUS_POINTER)


def _atomic_promote(candidate_dir: Path) -> None:
    """Stage, verify, and atomically switch the accepted version."""
    # 1. Compute the immutable directory name for the new version
    model_hash = _sha256(candidate_dir / "model.joblib")[:8]
    new_version_name = f"version-{model_hash}"
    new_version_path = MODELS_DIR / new_version_name

    # 2. Stage the complete bundle in a temporary directory
    with tempfile.TemporaryDirectory(dir=MODELS_DIR) as temp_dir:
        staging = Path(temp_dir)
        for name in REQUIRED_FILES:
            shutil.copy2(candidate_dir / name, staging / name)

        # 3. Verify the staged bundle before making it active
        for name in REQUIRED_FILES:
            if not (staging / name).exists():
                raise ValueError(f"Staging failed for {name}")

        # 4. Move staging to its final immutable directory
        if new_version_path.exists():
            shutil.rmtree(new_version_path)
        shutil.move(str(staging), str(new_version_path))

    # 5. Update both pointers only after staging is fully complete
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
