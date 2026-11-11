"""Week 5: score the already-selected model ONCE on the held test period.

Refuses to run if a result already exists, so the test score cannot be
re-run or used to choose between models.

Usage:
  uv run --locked python held_test_once.py \
      --model artifacts/model.joblib \
      --expected-sha256 fd98ceafc57a5babce61ce703cbf9cb8d1f83c6820b0b34fe30ad1a0fc49c304
"""

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

FEATURES = [
    "season",
    "yr",
    "mnth",
    "hr",
    "holiday",
    "weekday",
    "workingday",
    "weathersit",
    "temp",
    "atemp",
    "hum",
    "windspeed",
]
TARGET = "cnt"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, type=Path)
    ap.add_argument("--expected-sha256", required=True)
    ap.add_argument("--data", default=Path("data/raw/hour.csv"), type=Path)
    ap.add_argument("--out", default=Path("evidence/final/held-test.json"), type=Path)
    a = ap.parse_args()

    if a.out.exists():
        raise SystemExit(f"{a.out} already exists: the held test is scored only once.")

    model_sha = sha256(a.model)
    if model_sha != a.expected_sha256:
        raise SystemExit(
            f"Model sha256 {model_sha} does not match the selected model; not scoring."
        )

    df = pd.read_csv(a.data, parse_dates=["dteday"]).sort_values(
        ["dteday", "hr", "instant"]
    )
    train = df[(df.dteday >= "2011-01-01") & (df.dteday <= "2011-12-31")]
    test = df[(df.dteday >= "2012-07-01") & (df.dteday <= "2012-12-31")]
    assert len(train) == 8645, f"train rows {len(train)} != 8645"
    assert len(test) == 4376, f"test rows {len(test)} != 4376"

    model = joblib.load(a.model)
    cols = list(getattr(model, "feature_names_in_", FEATURES))
    y = test[TARGET].to_numpy()
    pred = np.asarray(model.predict(test[cols]), dtype=float)
    train_mean = float(train[TARGET].mean())

    record = {
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_sha": subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True
        ).stdout.strip(),
        "data_sha256": sha256(a.data),
        "test_window": "2012-07-01..2012-12-31",
        "test_rows": int(len(test)),
        "selected_model": {
            "path": str(a.model),
            "sha256": model_sha,
            "mae": float(np.mean(np.abs(pred - y))),
            "all_finite": bool(np.isfinite(pred).all()),
        },
        "train_mean_baseline": {
            "train_mean": train_mean,
            "mae": float(np.mean(np.abs(train_mean - y))),
        },
        "note": "Scored once on the already-selected model; not used for model selection or tuning.",
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(record, indent=2))
    print(
        f"held test ({len(test)} rows) | selected model MAE {record['selected_model']['mae']:.2f} "
        f"| train-mean MAE {record['train_mean_baseline']['mae']:.2f}"
    )
    print(f"written: {a.out}")


if __name__ == "__main__":
    main()
