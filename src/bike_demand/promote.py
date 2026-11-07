import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

CANDIDATE_DIR = Path("artifacts")
ACCEPTED_DIR = Path("models/accepted")
PREVIOUS_DIR = Path("models/previous")
REQUIRED_FILES = ("model.joblib", "model-metadata.json")


def _check_candidate() -> None:
    for name in REQUIRED_FILES:
        path = CANDIDATE_DIR / name
        if not path.exists():
            raise FileNotFoundError(f"Candidate file missing: {path}")


def _backup_accepted() -> None:
    if not ACCEPTED_DIR.exists() or not any(ACCEPTED_DIR.iterdir()):
        print("No accepted bundle to back up.")
        return
    PREVIOUS_DIR.mkdir(parents=True, exist_ok=True)
    for item in PREVIOUS_DIR.iterdir():
        if item.is_file():
            item.unlink()
    for name in REQUIRED_FILES:
        src = ACCEPTED_DIR / name
        if src.exists():
            shutil.copy2(src, PREVIOUS_DIR / name)
    print(f"Backed up accepted bundle to {PREVIOUS_DIR}")


def _promote_candidate() -> dict:
    ACCEPTED_DIR.mkdir(parents=True, exist_ok=True)
    for name in REQUIRED_FILES:
        shutil.copy2(CANDIDATE_DIR / name, ACCEPTED_DIR / name)
    metadata = json.loads((ACCEPTED_DIR / "model-metadata.json").read_text())
    metadata["promoted_at"] = datetime.now(timezone.utc).isoformat()
    (ACCEPTED_DIR / "model-metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    return metadata


def main() -> int:
    try:
        _check_candidate()
        _backup_accepted()
        metadata = _promote_candidate()
    except (FileNotFoundError, OSError, ValueError) as error:
        print(f"Promotion failed: {error}", file=sys.stderr)
        return 1
    print("Promotion complete.")
    print(f"Accepted model_version: {metadata.get('model_version')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
