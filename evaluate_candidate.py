"""Lab 7 Member 2: evaluate a candidate against the accepted model and the
train-mean baseline on the same validation rows, then apply the team gate.

Writes evidence only; never touches the accepted model.

Usage:
  uv run --locked python evaluate_candidate.py \
      --candidate artifacts/candidates/candidate-XXXX \
      --accepted models/accepted \
      --label normal
"""

import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

FEATURES = ["season", "yr", "mnth", "hr", "holiday", "weekday", "workingday",
            "weathersit", "temp", "atemp", "hum", "windspeed"]
TARGET = "cnt"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dir_hashes(path: Path) -> dict:
    files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
    return {str(p): sha256(p) for p in files}


def find_model(path: Path) -> Path:
    if path.is_file():
        return path
    for name in ("model.joblib", "model.pkl"):
        if (path / name).exists():
            return path / name
    found = sorted(path.rglob("*.joblib")) + sorted(path.rglob("*.pkl"))
    if not found:
        raise SystemExit(f"No model file found in {path}")
    return found[0]


def load_splits(data: Path):
    df = pd.read_csv(data, parse_dates=["dteday"])
    df = df.sort_values(["dteday", "hr", "instant"])
    train = df[(df.dteday >= "2011-01-01") & (df.dteday <= "2011-12-31")]
    val = df[(df.dteday >= "2012-01-01") & (df.dteday <= "2012-06-30")]
    assert len(train) == 8645, f"train rows {len(train)} != 8645"
    assert len(val) == 4358, f"validation rows {len(val)} != 4358"
    return train, val


def evaluate(model, X: pd.DataFrame, y: pd.Series) -> dict:
    cols = list(getattr(model, "feature_names_in_", FEATURES))
    X = X[cols]
    start = time.perf_counter()
    pred = np.asarray(model.predict(X), dtype=float)
    batch_s = time.perf_counter() - start
    single = []
    for i in range(50):
        row = X.iloc[[i]]
        t = time.perf_counter()
        model.predict(row)
        single.append((time.perf_counter() - t) * 1000)
    return {
        "mae": float(np.mean(np.abs(pred - y.to_numpy()))),
        "n_rows": int(len(y)),
        "all_finite": bool(np.isfinite(pred).all()),
        "batch_predict_seconds": round(batch_s, 4),
        "single_row_p95_ms": round(float(np.percentile(single, 95)), 3),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True, type=Path)
    ap.add_argument("--accepted", required=True, type=Path)
    ap.add_argument("--data", default=Path("data/raw/hour.csv"), type=Path)
    ap.add_argument("--label", required=True, help="e.g. normal or weak")
    ap.add_argument("--out", default=Path("evidence/lab7/evaluation"), type=Path)
    a = ap.parse_args()

    accepted_before = dir_hashes(a.accepted)
    train, val = load_splits(a.data)
    X, y = val[FEATURES], val[TARGET]

    cand_file, acc_file = find_model(a.candidate), find_model(a.accepted)
    cand = evaluate(joblib.load(cand_file), X, y)
    acc = evaluate(joblib.load(acc_file), X, y)
    train_mean = float(train[TARGET].mean())
    naive_mae = float(np.mean(np.abs(train_mean - y.to_numpy())))

    try:
        from bike_demand.gate import evaluate_quality_gate
        outcome, reasons = evaluate_quality_gate({"mae": cand["mae"]}, {"mae": acc["mae"]})
    except Exception as e:  # gate unavailable -> never count as pass
        outcome, reasons = "Blocked/Error", [f"Gate could not run: {e}"]

    accepted_after = dir_hashes(a.accepted)
    git_sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()

    record = {
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_sha": git_sha,
        "data": {"path": str(a.data), "sha256": sha256(a.data),
                 "validation_window": "2012-01-01..2012-06-30", "validation_rows": len(val)},
        "candidate": {"path": str(cand_file), "sha256": sha256(cand_file), **cand},
        "accepted": {"path": str(acc_file), "sha256": sha256(acc_file), **acc},
        "train_mean_baseline": {"train_mean": train_mean, "mae": naive_mae},
        "candidate_beats_train_mean": cand["mae"] < naive_mae,
        "gate": {"policy_file": "src/bike_demand/gate.py",
                 "policy_sha256": sha256(Path("src/bike_demand/gate.py")),
                 "outcome": outcome, "reasons": reasons},
        "accepted_unchanged": accepted_before == accepted_after,
        "accepted_hashes": accepted_after,
    }
    a.out.mkdir(parents=True, exist_ok=True)
    out = a.out / f"evaluation-{a.label}.json"
    out.write_text(json.dumps(record, indent=2))
    print(f"candidate MAE {cand['mae']:.2f} | accepted MAE {acc['mae']:.2f} | "
          f"train-mean MAE {naive_mae:.2f}")
    print(f"gate: {outcome} | accepted unchanged: {record['accepted_unchanged']}")
    print(f"written: {out}")


if __name__ == "__main__":
    main()
