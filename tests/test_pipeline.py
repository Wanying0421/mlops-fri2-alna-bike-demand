"""Synthetic integration tests; these are not course-model gate evidence."""

import json
import shutil
import subprocess
from pathlib import Path

import joblib
import pytest
import yaml

from bike_demand import pipeline
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
