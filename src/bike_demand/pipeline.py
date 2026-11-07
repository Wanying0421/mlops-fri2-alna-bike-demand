"""Lab 7 input checks and candidate training; no evaluation or promotion."""

import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
from datetime import UTC, datetime
from importlib.metadata import distributions
from pathlib import Path
from uuid import uuid4

import joblib
import yaml
from sklearn.ensemble import RandomForestRegressor

from bike_demand.bundles import verify_candidate_bundle
from bike_demand.preflight import check_snapshot, sha256
from bike_demand.split import partition_summary, split_data
from bike_demand.validate import FEATURES, load_data


def write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def load_candidate_config(path: Path) -> dict:
    """Keep the data contract fixed; allow bounded, reviewed RF settings."""
    config = yaml.safe_load(path.read_bytes())
    if not isinstance(config, dict) or set(config) != {"data", "features", "model"}:
        raise ValueError("config: require exactly data, features and model")
    if config["data"] != "data/raw/hour.csv":
        raise ValueError("config: require the frozen data/raw/hour.csv")
    if config["features"] != list(FEATURES):
        raise ValueError("config: require the twelve ordered features")
    model = config["model"]
    bounds = {
        "n_estimators": (1, 200),
        "max_depth": (1, 20),
        "random_state": (0, 2**32 - 1),
        "n_jobs": (1, 1),
    }
    if not isinstance(model, dict) or set(model) != set(bounds):
        raise ValueError("model: require n_estimators, max_depth, random_state, n_jobs")
    for name, (lower, upper) in bounds.items():
        if type(model[name]) is not int or not lower <= model[name] <= upper:
            raise ValueError(f"model.{name}: require an integer in [{lower}, {upper}]")
    return config


def inspect_inputs(root: Path, config_path: Path) -> tuple[dict, dict, dict]:
    config = load_candidate_config(config_path)
    manifest = check_snapshot(root)
    parts = split_data(load_data(root / config["data"]))
    if manifest.get("partition_rows") != {
        name: len(part) for name, part in parts.items()
    }:
        raise ValueError("data: partition counts do not match the frozen manifest")
    summaries = partition_summary(parts)
    for name, part in parts.items():
        # Frozen dataset digest + ordered instant IDs identify the observations.
        ids = json.dumps(
            [int(value) for value in part["instant"]], separators=(",", ":")
        )
        summaries[name]["ordered_ids_sha256"] = hashlib.sha256(ids.encode()).hexdigest()
    return config, parts, summaries


def git_output(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=False
    )
    if result.returncode:
        raise ValueError("source: require a Git checkout with a committed HEAD")
    return result.stdout.strip()


def source_identity(root: Path, config_path: Path) -> dict:
    """Reject uncommitted training inputs, allowing unrelated untracked files."""
    if Path(git_output(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise ValueError("source: run from the repository root")
    commit = git_output(root, "rev-parse", "HEAD")
    if not re.fullmatch(r"[0-9a-f]{40,64}", commit):
        raise ValueError("source: invalid Git revision")
    config_name = config_path.relative_to(root).as_posix()
    git_output(root, "ls-files", "--error-unmatch", "--", config_name)
    if git_output(root, "diff", "HEAD", "--name-only"):
        raise ValueError("source: commit tracked changes before training")
    if git_output(
        root,
        "ls-files",
        "--others",
        "--exclude-standard",
        "--",
        "src",
        "configs",
        "data",
        "pyproject.toml",
        "uv.lock",
        ".python-version",
    ):
        raise ValueError("source: commit untracked training inputs before training")
    return {"training_commit": commit, "tracked_tree_clean": True}


def train_candidate(
    root: Path, config_path: Path, candidate_id: str | None = None
) -> Path:
    """Write a new bundle. Never change the accepted model or its reports."""
    root, config_path = root.resolve(), config_path.resolve()
    config_path.relative_to(root)  # Config must be inside the same checkout.
    candidate_id = candidate_id or f"candidate-{uuid4().hex}"
    if not re.fullmatch(r"candidate-[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}", candidate_id):
        raise ValueError("candidate ID: use candidate- followed by letters/digits/_/-")
    source = source_identity(root, config_path)
    lock_path = root / "uv.lock"
    # Check these identities again before publishing, detecting mid-run edits.
    inputs = {
        name: sha256(path)
        for name, path in {
            "config": config_path,
            "data": root / "data/raw/hour.csv",
            "data_manifest": root / "data/manifest.json",
            "lock": lock_path,
        }.items()
    }
    config, parts, summaries = inspect_inputs(root, config_path)
    parent = root / "artifacts/candidates"
    if parent.resolve() != parent:
        raise ValueError("output: artifacts/candidates must not traverse a symlink")
    parent.mkdir(parents=True, exist_ok=True)
    destination = parent / candidate_id
    # Exclusive mkdir reserves an ID, including after an interrupted attempt.
    destination.mkdir(exist_ok=False)
    try:
        model = RandomForestRegressor(**config["model"])
        train = parts["train"]
        model.fit(train.loc[:, list(FEATURES)], train["cnt"])
        model_path = destination / "model.joblib"
        joblib.dump(model, model_path)
        metadata = {
            "schema_version": 1,
            "model_version": candidate_id,
            "created_at": datetime.now(UTC).isoformat(),
            **source,
            "features": list(FEATURES),
            "data_sha256": inputs["data"],
            "config_sha256": inputs["config"],
            "uv_lock_sha256": inputs["lock"],
            "model_sha256": sha256(model_path),
            "model_parameters": model.get_params(),
            "random_seed": config["model"]["random_state"],
            "training_rows": len(train),
            "evaluation_status": "not_evaluated",
        }
        write_json(destination / "model-metadata.json", metadata)
        write_json(destination / "partitions.json", summaries)
        write_json(
            destination / "environment.json",
            {
                "python": sys.version,
                "platform": platform.platform(),
                "packages": dict(
                    sorted(
                        (dist.metadata["Name"], dist.version)
                        for dist in distributions()
                    )
                ),
            },
        )
        for source_path, name in (
            (config_path, "config.yaml"),
            (lock_path, "uv.lock"),
            (root / "data/manifest.json", "data-manifest.json"),
        ):
            (destination / name).write_bytes(source_path.read_bytes())
        current = {
            "config": sha256(config_path),
            "data": sha256(root / config["data"]),
            "data_manifest": sha256(root / "data/manifest.json"),
            "lock": sha256(lock_path),
        }
        if current != inputs or source_identity(root, config_path) != source:
            raise ValueError(
                "inputs/source changed during training; candidate incomplete"
            )
        bundle = {
            "schema_version": 1,
            "candidate_id": candidate_id,
            "stage": "trained",
            "evaluation_status": "not_evaluated",
            "files": {
                path.name: {"sha256": sha256(path), "bytes": path.stat().st_size}
                for path in sorted(destination.iterdir())
            },
        }
        # This final marker is the only signal that the training bundle is complete.
        temporary = destination / "bundle.json.tmp"
        write_json(temporary, bundle)
        temporary.replace(destination / "bundle.json")
    except Exception as error:
        write_json(
            destination / "failure.json", {"stage": "train", "reason": str(error)}
        )
        raise
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("check", "train", "verify"))
    parser.add_argument("--config", type=Path, default=Path("configs/baseline.yaml"))
    parser.add_argument("--candidate-id", help="Optional write-once candidate-... ID")
    parser.add_argument("--candidate-dir", type=Path, help="Completed bundle to verify")
    parser.add_argument(
        "--expected-bundle-sha256", help="Previously recorded manifest digest"
    )
    args = parser.parse_args()
    try:
        if args.stage == "check":
            _, _, summaries = inspect_inputs(Path.cwd(), args.config)
            result = {"status": "inputs_validated", "partitions": summaries}
        elif args.stage == "verify":
            if args.candidate_dir is None:
                raise ValueError("verify: require --candidate-dir")
            verification = verify_candidate_bundle(
                args.candidate_dir, args.expected_bundle_sha256
            )
            result = {
                "status": "bundle_verified",
                "candidate_id": verification["manifest"]["candidate_id"],
                "bundle_sha256": verification["bundle_sha256"],
                "evaluation_status": "not_evaluated",
            }
        else:
            path = train_candidate(Path.cwd(), args.config, args.candidate_id)
            result = {
                "status": "trained",
                "candidate_dir": str(path),
                "evaluation_status": "not_evaluated",
            }
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as error:
        print(json.dumps({"status": "error", "reason": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
