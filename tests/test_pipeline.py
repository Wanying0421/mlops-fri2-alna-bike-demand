"""Synthetic integration tests; these are not course-model gate evidence."""

import json
import shutil
import subprocess
from pathlib import Path

import joblib
import pytest
import yaml

from bike_demand import bundles, pipeline
from bike_demand.preflight import sha256
from bike_demand.validate import FEATURES, load_data


@pytest.fixture
def checkout(tmp_path):
    (tmp_path / "data/raw").mkdir(parents=True)
    (tmp_path / "configs").mkdir()
    data = tmp_path / "data/raw/hour.csv"
    shutil.copyfile(Path(__file__).parent / "fixtures/missing-hours.csv", data)
    frame = load_data(data)
    manifest = {
        "sha256": sha256(data),
        "bytes": data.stat().st_size,
        "header": list(frame.columns),
        "rows": len(frame),
        "partition_rows": {"train": 2, "validation": 2, "test": 2},
    }
    (tmp_path / "data/manifest.json").write_text(json.dumps(manifest))
    config = yaml.safe_load(Path("configs/baseline.yaml").read_text())
    config["model"]["n_estimators"] = 2
    (tmp_path / "configs/baseline.yaml").write_text(yaml.safe_dump(config))
    # Fixture only: no claim that this is the real dependency lock or a course run.
    (tmp_path / "uv.lock").write_text("synthetic-test-lock\n")
    (tmp_path / ".gitignore").write_text("artifacts/\nreports/\ntracking/\n")
    for args in (
        ("init", "-q"),
        ("add", "."),
        (
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-qm",
            "Create synthetic fixture",
        ),
    ):
        subprocess.run(
            ["git", "-C", str(tmp_path), *args], check=True, capture_output=True
        )
    return tmp_path


def test_candidate_is_separate_complete_and_train_only(checkout, monkeypatch):
    protected = {}
    for name in (
        "artifacts/model.joblib",
        "artifacts/model-metadata.json",
        "artifacts/accepted.json",
        "reports/metrics.json",
        "reports/metrics-history.jsonl",
        "tracking/mlflow.db",
    ):
        path = checkout / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"existing accepted state: do not overwrite\n")
        protected[path] = path.read_bytes()
    fit = pipeline.RandomForestRegressor.fit

    def train_only(self, features, labels):
        assert list(features.columns) == list(FEATURES)
        assert list(features.index) == [0, 1]
        assert list(labels) == [10, 30]
        return fit(self, features, labels)

    def no_evaluation(*args, **kwargs):
        pytest.fail("Member 1 training must not score validation or held-test rows")

    monkeypatch.setattr(pipeline.RandomForestRegressor, "fit", train_only)
    monkeypatch.setattr(pipeline.RandomForestRegressor, "predict", no_evaluation)
    (checkout / "unrelated-note.txt").write_text("Unrelated untracked file is allowed.")
    candidate = pipeline.train_candidate(
        checkout, checkout / "configs/baseline.yaml", "candidate-fixture"
    )
    assert all(path.read_bytes() == content for path, content in protected.items())
    bundle = json.loads((candidate / "bundle.json").read_text())
    assert bundle["evaluation_status"] == "not_evaluated"
    assert set(bundle["files"]) == {
        "model.joblib",
        "model-metadata.json",
        "config.yaml",
        "uv.lock",
        "data-manifest.json",
        "environment.json",
        "partitions.json",
    }
    for name, identity in bundle["files"].items():
        assert identity == {
            "sha256": sha256(candidate / name),
            "bytes": (candidate / name).stat().st_size,
        }
    meta = json.loads((candidate / "model-metadata.json").read_text())
    assert meta["training_commit"] == pipeline.git_output(checkout, "rev-parse", "HEAD")
    assert meta["model_sha256"] == sha256(candidate / "model.joblib")
    assert meta["data_sha256"] == sha256(checkout / "data/raw/hour.csv")
    assert meta["config_sha256"] == sha256(candidate / "config.yaml")
    assert meta["uv_lock_sha256"] == sha256(candidate / "uv.lock")
    assert meta["training_rows"] == 2
    assert list(joblib.load(candidate / "model.joblib").feature_names_in_) == list(
        FEATURES
    )
    before = {path.name: path.read_bytes() for path in candidate.iterdir()}
    with pytest.raises(FileExistsError):
        pipeline.train_candidate(
            checkout, checkout / "configs/baseline.yaml", "candidate-fixture"
        )
    assert before == {path.name: path.read_bytes() for path in candidate.iterdir()}


def test_interrupted_fit_never_publishes_a_complete_candidate(checkout, monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError("synthetic training failure")

    monkeypatch.setattr(pipeline.RandomForestRegressor, "fit", fail)
    with pytest.raises(ValueError, match="synthetic training failure"):
        pipeline.train_candidate(
            checkout, checkout / "configs/baseline.yaml", "candidate-failed"
        )
    output = checkout / "artifacts/candidates/candidate-failed"
    assert not (output / "bundle.json").exists()
    assert "synthetic training failure" in (output / "failure.json").read_text()
    with pytest.raises(FileExistsError):
        pipeline.train_candidate(
            checkout, checkout / "configs/baseline.yaml", "candidate-failed"
        )


def test_midrun_input_change_does_not_publish(checkout, monkeypatch):
    fit = pipeline.RandomForestRegressor.fit

    def change_input(self, features, labels):
        result = fit(self, features, labels)
        with (checkout / "uv.lock").open("a") as stream:
            stream.write("changed during fit\n")
        return result

    monkeypatch.setattr(pipeline.RandomForestRegressor, "fit", change_input)
    with pytest.raises(ValueError, match="inputs/source changed"):
        pipeline.train_candidate(
            checkout, checkout / "configs/baseline.yaml", "candidate-changed"
        )
    assert not (
        checkout / "artifacts/candidates/candidate-changed/bundle.json"
    ).exists()


def test_uncommitted_source_is_not_claimed_as_a_committed_run(checkout):
    config = checkout / "configs/baseline.yaml"
    config.write_text(config.read_text() + "\n# uncommitted change\n")
    with pytest.raises(ValueError, match="commit tracked changes"):
        pipeline.train_candidate(checkout, config)
    assert not (checkout / "artifacts/candidates").exists()


@pytest.mark.parametrize(
    "setting,value",
    [
        ("n_estimators", True),
        ("n_estimators", 201),
        ("max_depth", None),
        ("random_state", -1),
        ("n_jobs", -1),
    ],
)
def test_invalid_or_unbounded_settings_fail_before_fitting(tmp_path, setting, value):
    config = yaml.safe_load(Path("configs/baseline.yaml").read_text())
    config["model"][setting] = value
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match=setting):
        pipeline.load_candidate_config(path)


def test_path_traversal_cannot_target_the_accepted_model(checkout):
    with pytest.raises(ValueError, match="candidate ID"):
        pipeline.train_candidate(
            checkout, checkout / "configs/baseline.yaml", "../model"
        )


@pytest.fixture
def candidate(checkout):
    return pipeline.train_candidate(
        checkout, checkout / "configs/baseline.yaml", "candidate-review-fixture"
    )


def test_verified_bundle_loads_the_original_trusted_model(candidate):
    before = {path.name: path.read_bytes() for path in candidate.iterdir()}
    expected = sha256(candidate / "bundle.json")
    model, verification = bundles.load_verified_model(candidate, expected.upper())
    assert list(model.feature_names_in_) == list(FEATURES)
    assert verification["bundle_sha256"] == expected
    assert verification["metadata"]["training_rows"] == 2
    assert before == {path.name: path.read_bytes() for path in candidate.iterdir()}


@pytest.mark.parametrize("name", sorted(bundles.BUNDLE_FILES))
def test_changed_bundle_file_is_rejected_before_deserialization(
    candidate, monkeypatch, name
):
    path = candidate / name
    original = path.read_bytes()
    # Keep the same length so a digest mismatch cannot be hidden by a size check.
    path.write_bytes(bytes([original[0] ^ 1]) + original[1:])
    before = {path.name: path.read_bytes() for path in candidate.iterdir()}

    def forbidden(*args, **kwargs):
        pytest.fail("Corrupted bundles must never reach joblib.load")

    monkeypatch.setattr(bundles.joblib, "load", forbidden)
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        bundles.load_verified_model(candidate)
    assert before == {path.name: path.read_bytes() for path in candidate.iterdir()}


@pytest.mark.parametrize(
    "fault",
    [
        "digest",
        "size",
        "negative_size",
        "boolean_size",
        "invalid_digest",
        "schema",
        "boolean_schema",
        "missing_entry",
        "traversal",
        "absolute_path",
        "wrong_stage",
        "wrong_status",
        "missing_manifest",
        "invalid_json",
        "duplicate_key",
        "nonfinite",
    ],
)
def test_corrupted_manifest_is_rejected_before_loading(candidate, monkeypatch, fault):
    path = candidate / "bundle.json"
    manifest = json.loads(path.read_bytes())
    entry = manifest["files"]["model.joblib"]
    if fault == "digest":
        entry["sha256"] = "0" * 64
    elif fault == "size":
        entry["bytes"] += 1
    elif fault == "negative_size":
        entry["bytes"] = -1
    elif fault == "boolean_size":
        entry["bytes"] = True
    elif fault == "invalid_digest":
        entry["sha256"] = "not-a-sha256"
    elif fault == "schema":
        manifest["schema_version"] = 999
    elif fault == "boolean_schema":
        manifest["schema_version"] = True
    elif fault == "missing_entry":
        del manifest["files"]["model.joblib"]
    elif fault == "traversal":
        manifest["files"]["../model.joblib"] = manifest["files"].pop("model.joblib")
    elif fault == "absolute_path":
        manifest["files"]["/model.joblib"] = manifest["files"].pop("model.joblib")
    elif fault == "wrong_stage":
        manifest["stage"] = "training"
    elif fault == "wrong_status":
        manifest["evaluation_status"] = "eligible"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    if fault == "missing_manifest":
        path.unlink()
    elif fault == "invalid_json":
        path.write_text("{incomplete", encoding="utf-8")
    elif fault == "duplicate_key":
        path.write_text('{"schema_version": 1, "schema_version": 1}', encoding="utf-8")
    elif fault == "nonfinite":
        path.write_text('{"schema_version": NaN}', encoding="utf-8")

    def forbidden(*args, **kwargs):
        pytest.fail("Invalid manifests must never reach joblib.load")

    monkeypatch.setattr(bundles.joblib, "load", forbidden)
    with pytest.raises(ValueError):
        bundles.load_verified_model(candidate)


def test_recorded_manifest_digest_binds_the_exact_manifest(candidate):
    expected = sha256(candidate / "bundle.json")
    with (candidate / "bundle.json").open("ab") as stream:
        stream.write(b"\n")  # Valid JSON; a pinned byte identity must still fail.
    with pytest.raises(ValueError, match="trusted bundle.json SHA-256 mismatch"):
        bundles.verify_candidate_bundle(candidate, expected)


@pytest.mark.parametrize("name", ["model.joblib", "model-metadata.json"])
def test_missing_required_file_is_rejected(candidate, name):
    (candidate / name).unlink()
    with pytest.raises(ValueError, match="missing or unexpected files"):
        bundles.verify_candidate_bundle(candidate)


def test_loader_uses_the_verified_memory_copy(candidate, monkeypatch):
    original_load = bundles.joblib.load
    original_model_hash = sha256(candidate / "model.joblib")

    def replace_path_before_deserialization(stream):
        assert hasattr(stream, "read")  # The loader must not reopen a mutable path.
        (candidate / "model.joblib").write_bytes(b"synthetic replacement after read")
        return original_load(stream)

    monkeypatch.setattr(bundles.joblib, "load", replace_path_before_deserialization)
    model, verified = bundles.load_verified_model(candidate)
    assert list(model.feature_names_in_) == list(FEATURES)
    assert verified["metadata"]["model_sha256"] == original_model_hash
    assert sha256(candidate / "model.joblib") != original_model_hash


@pytest.mark.parametrize(
    "field,value",
    [
        ("model_version", "candidate-other"),
        ("model_sha256", "0" * 64),
        ("data_sha256", "0" * 64),
        ("features", list(reversed(FEATURES))),
        ("training_rows", 999),
        ("random_seed", None),
        ("training_commit", "unavailable"),
    ],
)
def test_metadata_cross_references_are_checked(candidate, field, value):
    path = candidate / "model-metadata.json"
    meta = json.loads(path.read_bytes())
    meta[field] = value
    path.write_text(json.dumps(meta), encoding="utf-8")
    manifest_path = candidate / "bundle.json"
    manifest = json.loads(manifest_path.read_bytes())
    # Simulate a self-consistent checksum update: semantic cross-references still fail.
    manifest["files"][path.name] = {
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError):
        bundles.verify_candidate_bundle(candidate)


def test_model_replacement_after_verification_is_rejected(candidate, monkeypatch):
    original_verify = bundles.verify_candidate_bundle

    def replace_after_verify(*args):
        result = original_verify(*args)
        with (candidate / "model.joblib").open("ab") as stream:
            stream.write(b"changed after verification")
        return result

    def forbidden(*args, **kwargs):
        pytest.fail("Replaced model bytes must never reach joblib.load")

    monkeypatch.setattr(bundles, "verify_candidate_bundle", replace_after_verify)
    monkeypatch.setattr(bundles.joblib, "load", forbidden)
    with pytest.raises(ValueError, match="mismatch"):
        bundles.load_verified_model(candidate)


@pytest.mark.parametrize("corrupt", [False, True])
def test_verify_cli_reports_the_selected_bundle(
    candidate, monkeypatch, capsys, corrupt
):
    if corrupt:
        manifest_path = candidate / "bundle.json"
        manifest = json.loads(manifest_path.read_bytes())
        manifest["files"]["model.joblib"]["sha256"] = "0" * 64
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv", ["pipeline", "verify", "--candidate-dir", str(candidate)]
    )
    assert pipeline.main() == (1 if corrupt else 0)
    output = capsys.readouterr()
    if corrupt:
        assert "SHA-256 mismatch for model.joblib" in output.err
        assert output.out == ""
    else:
        assert json.loads(output.out)["status"] == "bundle_verified"
