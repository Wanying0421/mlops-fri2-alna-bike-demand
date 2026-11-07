"""Check training bundle bytes before loading a model from a trusted source.

Hashes establish byte identity, not trust in arbitrary pickle files. Evaluation,
gate policy and accepted-state updates are separate responsibilities.
"""

import hashlib
import io
import json
import re
from pathlib import Path

import joblib

from bike_demand.validate import FEATURES

BUNDLE_FILES = frozenset(
    {
        "model.joblib",
        "model-metadata.json",
        "config.yaml",
        "uv.lock",
        "data-manifest.json",
        "environment.json",
        "partitions.json",
    }
)


def _object(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"bundle: duplicate JSON key {key!r}")
        result[key] = value
    return result


def _invalid_constant(value: str):
    raise ValueError(f"bundle: non-finite JSON value {value}")


def _json(raw: bytes, name: str) -> dict:
    try:
        value = json.loads(
            raw, object_pairs_hook=_object, parse_constant=_invalid_constant
        )
    except (ValueError, UnicodeError) as error:
        raise ValueError(f"bundle: invalid {name}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"bundle: {name} must contain a JSON object")
    return value


def _digest(value, name: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", value):
        raise ValueError(f"bundle: invalid SHA-256 for {name}")
    return value.lower()


def _read_file(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"bundle: missing or non-regular file {path.name}")
    return path.read_bytes()


def _check_bytes(raw: bytes, identity: dict, name: str) -> None:
    if not isinstance(identity, dict) or set(identity) != {"bytes", "sha256"}:
        raise ValueError(f"bundle: invalid file identity for {name}")
    size = identity["bytes"]
    if type(size) is not int or size < 0:
        raise ValueError(f"bundle: invalid byte count for {name}")
    expected = _digest(identity["sha256"], name)
    if len(raw) != size:
        raise ValueError(f"bundle: byte count mismatch for {name}")
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f"bundle: SHA-256 mismatch for {name}")


def verify_candidate_bundle(
    candidate_dir: Path, expected_bundle_sha256: str | None = None
) -> dict:
    """Read-only verification; never deserialize model.joblib or issue a decision.

    Supply an independently recorded manifest digest to bind verification to a
    specific previously recorded bundle. Self-consistent hashes alone do not prove
    authenticity, training correctness or policy eligibility.
    """
    directory = Path(candidate_dir)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("bundle: candidate directory is missing or is a symlink")
    raw_manifest = _read_file(directory / "bundle.json")
    manifest_digest = hashlib.sha256(raw_manifest).hexdigest()
    if expected_bundle_sha256 is not None:
        if manifest_digest != _digest(expected_bundle_sha256, "bundle.json"):
            raise ValueError("bundle: trusted bundle.json SHA-256 mismatch")
    manifest = _json(raw_manifest, "bundle.json")
    if set(manifest) != {
        "schema_version",
        "candidate_id",
        "stage",
        "evaluation_status",
        "files",
    }:
        raise ValueError("bundle: invalid manifest fields")
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1:
        raise ValueError("bundle: unsupported schema_version")
    identifier = manifest["candidate_id"]
    if not isinstance(identifier, str) or not re.fullmatch(
        r"candidate-[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}", identifier
    ):
        raise ValueError("bundle: invalid candidate_id")
    if (
        manifest["stage"] != "trained"
        or manifest["evaluation_status"] != "not_evaluated"
    ):
        raise ValueError("bundle: require a complete, unevaluated training bundle")
    files = manifest["files"]
    # Exact allowlist rejects missing entries, absolute paths and traversal names.
    if not isinstance(files, dict) or set(files) != BUNDLE_FILES:
        raise ValueError("bundle: files must contain exactly the seven expected names")
    if {path.name for path in directory.iterdir()} != BUNDLE_FILES | {"bundle.json"}:
        raise ValueError("bundle: directory contains missing or unexpected files")
    documents = {}
    for name in sorted(BUNDLE_FILES):
        raw = _read_file(directory / name)
        _check_bytes(raw, files[name], name)
        if name.endswith(".json"):
            documents[name] = _json(raw, name)
    metadata = documents["model-metadata.json"]
    required_metadata = {
        "schema_version",
        "model_version",
        "created_at",
        "training_commit",
        "tracked_tree_clean",
        "features",
        "data_sha256",
        "config_sha256",
        "uv_lock_sha256",
        "model_sha256",
        "model_parameters",
        "random_seed",
        "training_rows",
        "evaluation_status",
    }
    if not required_metadata <= set(metadata):
        raise ValueError("bundle: missing required model metadata")
    if (
        type(metadata.get("schema_version")) is not int
        or metadata["schema_version"] != 1
    ):
        raise ValueError("bundle: unsupported metadata schema_version")
    if metadata.get("model_version") != identifier:
        raise ValueError("bundle: model_version does not match candidate_id")
    if metadata.get("evaluation_status") != "not_evaluated":
        raise ValueError("bundle: inconsistent metadata evaluation_status")
    if metadata.get("features") != list(FEATURES):
        raise ValueError("bundle: metadata features do not match the data contract")
    commit = metadata.get("training_commit")
    if not isinstance(commit, str) or not re.fullmatch(
        r"[0-9a-f]{40}|[0-9a-f]{64}", commit
    ):
        raise ValueError("bundle: invalid training_commit")
    if metadata.get("tracked_tree_clean") is not True:
        raise ValueError("bundle: training source was not recorded as clean")
    parameters = metadata["model_parameters"]
    seed = metadata["random_seed"]
    if (
        type(seed) is not int
        or not 0 <= seed < 2**32
        or not isinstance(parameters, dict)
        or parameters.get("random_state") != seed
    ):
        raise ValueError("bundle: inconsistent random seed")
    if not isinstance(metadata["created_at"], str) or not metadata["created_at"]:
        raise ValueError("bundle: missing training timestamp")
    for field, name in (
        ("model_sha256", "model.joblib"),
        ("config_sha256", "config.yaml"),
        ("uv_lock_sha256", "uv.lock"),
    ):
        if _digest(metadata.get(field), field) != _digest(files[name]["sha256"], name):
            raise ValueError(f"bundle: inconsistent metadata {field}")
    data = documents["data-manifest.json"]
    if _digest(metadata.get("data_sha256"), "data_sha256") != _digest(
        data.get("sha256"), "data manifest"
    ):
        raise ValueError("bundle: inconsistent data identity")
    partitions = documents["partitions.json"]
    counts = data.get("partition_rows")
    if not isinstance(counts, dict) or set(counts) != {"train", "validation", "test"}:
        raise ValueError("bundle: invalid dataset partition counts")
    if set(partitions) != set(counts):
        raise ValueError("bundle: inconsistent partition names")
    for name, count in counts.items():
        summary = partitions[name]
        if type(count) is not int or count <= 0 or not isinstance(summary, dict):
            raise ValueError("bundle: invalid dataset partition counts")
        if type(summary.get("rows")) is not int or summary["rows"] != count:
            raise ValueError(f"bundle: inconsistent {name} row count")
        _digest(summary.get("ordered_ids_sha256"), f"{name} observations")
    if (
        type(metadata.get("training_rows")) is not int
        or metadata["training_rows"] != counts["train"]
    ):
        raise ValueError("bundle: inconsistent training_rows")
    environment = documents["environment.json"]
    if (
        not isinstance(environment.get("python"), str)
        or not environment["python"]
        or not isinstance(environment.get("platform"), str)
        or not environment["platform"]
        or not isinstance(environment.get("packages"), dict)
        or not environment["packages"]
    ):
        raise ValueError("bundle: missing runtime environment")
    return {
        "manifest": manifest,
        "metadata": metadata,
        "bundle_sha256": manifest_digest,
    }


def load_verified_model(
    candidate_dir: Path, expected_bundle_sha256: str | None = None
) -> tuple[object, dict]:
    """Load only a trusted model, from the exact bytes checked immediately before it.

    The in-memory copy prevents a later replacement of the file path from changing
    the bytes passed to joblib.load. This does not make untrusted pickle files safe.
    """
    verification = verify_candidate_bundle(candidate_dir, expected_bundle_sha256)
    raw = _read_file(Path(candidate_dir) / "model.joblib")
    _check_bytes(raw, verification["manifest"]["files"]["model.joblib"], "model.joblib")
    return joblib.load(io.BytesIO(raw)), verification
