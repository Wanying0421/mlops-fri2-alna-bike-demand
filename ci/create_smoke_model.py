"""Create a tiny, explicitly labelled model for the CI container smoke check."""

import argparse
import hashlib
import json
import re
from pathlib import Path

import joblib
import pandas as pd
from sklearn.dummy import DummyRegressor

from bike_demand.validate import FEATURES


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--git-sha", required=True)
    args = parser.parse_args()

    if not re.fullmatch(r"[0-9a-fA-F]{40}", args.git_sha):
        parser.error("--git-sha must be a complete 40-character hexadecimal SHA")
    if args.output_dir.exists() and (
        not args.output_dir.is_dir() or any(args.output_dir.iterdir())
    ):
        parser.error("refusing to overwrite a non-empty output directory")

    # Synthetic inputs only: no course data, fitted baseline, or model-quality claim.
    sample = {
        "season": 2,
        "yr": 1,
        "mnth": 6,
        "hr": 12,
        "holiday": 0,
        "weekday": 3,
        "workingday": 1,
        "weathersit": 1,
        "temp": 0.6,
        "atemp": 0.6,
        "hum": 0.5,
        "windspeed": 0.2,
    }
    frame = pd.DataFrame([sample], columns=list(FEATURES))
    model = DummyRegressor(strategy="constant", constant=42.0).fit(frame, [42.0])

    args.output_dir.mkdir(parents=True, exist_ok=True)
    model_path = args.output_dir / "model.joblib"
    joblib.dump(model, model_path)
    metadata = {
        "model_version": f"ci-smoke-{args.git_sha.lower()}",
        "features": list(FEATURES),
        "source_commit": args.git_sha.lower(),
        "model_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
        "purpose": "CI-only synthetic fixture; not the evaluated or deployed baseline",
    }
    (args.output_dir / "model-metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metadata))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
