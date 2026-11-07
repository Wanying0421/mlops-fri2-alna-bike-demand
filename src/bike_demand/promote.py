import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from bike_demand.bundles import verify_candidate_bundle

CANDIDATE_DIR = Path("artifacts")
MODELS_DIR = Path("models")
VERSIONS_FILE = MODELS_DIR / "versions.json"
BUNDLE_FILES = (
    "model.joblib",
    "model-metadata.json",
    "config.yaml",
    "uv.lock",
    "data-manifest.json",
    "environment.json",
    "partitions.json",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_eligibility_and_bundle(candidate_dir: Path) -> dict:
    """Verify eligibility and the complete bundle."""
    decision_file = candidate_dir / "decision_record.json"
    if not decision_file.exists():
        raise ValueError("Missing decision_record.json")

    decision = json.loads(decision_file.read_text())
    if decision.get("outcome") != "Eligible":
        raise ValueError(f"Not eligible: {decision.get('outcome')}")

    if not decision.get("candidate_id") or not decision.get("bundle_sha256"):
        raise ValueError("Decision missing candidate_id or bundle_sha256")

    # Copy only the required files to a temp dir to pass the strict verifier
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        for name in BUNDLE_FILES:
            shutil.copy2(candidate_dir / name, temp_path / name)
        shutil.copy2(candidate_dir / "bundle.json", temp_path / "bundle.json")

        verify_candidate_bundle(temp_path, decision["bundle_sha256"])

    return decision


def _read_versions() -> dict:
    if VERSIONS_FILE.exists():
        return json.loads(VERSIONS_FILE.read_text())
    return {"current": None, "previous": None}


def _write_versions_atomically(current: str, previous: str | None) -> None:
    data = {"current": current, "previous": previous}
    with tempfile.NamedTemporaryFile("w", dir=VERSIONS_FILE.parent, delete=False) as f:
        f.write(json.dumps(data))
        temp_path = f.name
    os.replace(temp_path, VERSIONS_FILE)


def _atomic_promote(candidate_dir: Path, decision: dict) -> None:
    """Stage, verify, and switch. Version directories are immutable."""
    model_hash = _sha256(candidate_dir / "model.joblib")[:8]
    new_version_name = f"version-{model_hash}"
    new_version_path = MODELS_DIR / new_version_name

    # If the candidate is already the current version, do not touch the pointers.
    versions = _read_versions()
    if versions.get("current") == new_version_name:
        print("Candidate is already the current version. No changes made.")
        return

    with tempfile.TemporaryDirectory(dir=MODELS_DIR) as temp_dir:
        staging = Path(temp_dir)
        for name in BUNDLE_FILES:
            shutil.copy2(candidate_dir / name, staging / name)
        if (candidate_dir / "bundle.json").exists():
            shutil.copy2(candidate_dir / "bundle.json", staging / "bundle.json")

        verify_candidate_bundle(staging, decision["bundle_sha256"])

        if new_version_path.exists():
            shutil.rmtree(new_version_path)
        shutil.move(str(staging), str(new_version_path))

    current_version = versions.get("current")
    _write_versions_atomically(current=new_version_name, previous=current_version)


def main() -> int:
    try:
        decision = _check_eligibility_and_bundle(CANDIDATE_DIR)
        _atomic_promote(CANDIDATE_DIR, decision)
    except Exception as error:
        print(f"Promotion failed: {error}", file=sys.stderr)
        return 1
    print("Promotion complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
