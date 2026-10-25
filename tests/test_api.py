import pytest
from fastapi.testclient import TestClient

from bike_demand import api


@pytest.fixture
def valid_payload():
    return {
        "season": 1,
        "yr": 0,
        "mnth": 1,
        "hr": 10,
        "holiday": 0,
        "weekday": 1,
        "workingday": 1,
        "weathersit": 1,
        "temp": 0.3,
        "atemp": 0.3,
        "hum": 0.5,
        "windspeed": 0.2,
    }


@pytest.fixture
def client_without_model(monkeypatch, tmp_path):
    missing_model = tmp_path / "missing-model.joblib"
    monkeypatch.setenv("MODEL_PATH", str(missing_model))

    with TestClient(api.app) as client:
        yield client


def test_health_without_model_returns_503(client_without_model):
    response = client_without_model.get("/health")
    assert response.status_code == 503


def test_valid_request_without_model_returns_503(client_without_model, valid_payload):
    response = client_without_model.post("/predict", json=valid_payload)
    assert response.status_code == 503


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("hum", 1.5),
        ("hr", "hello"),
        ("hr", "10"),
        ("cnt", 100),
        ("casual", 10),
        ("registered", 90),
        ("unexpected_field", 1),
    ],
)
def test_invalid_request_returns_422(client_without_model, valid_payload, field, value):
    payload = {**valid_payload, field: value}
    response = client_without_model.post("/predict", json=payload)

    assert response.status_code == 422
    assert any(error["loc"] == ["body", field] for error in response.json()["detail"])


@pytest.mark.parametrize(
    "field",
    [
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
    ],
)
def test_missing_required_field_returns_422(client_without_model, valid_payload, field):
    valid_payload.pop(field)
    response = client_without_model.post("/predict", json=valid_payload)

    assert response.status_code == 422
    assert any(
        error["loc"] == ["body", field] and error["type"] == "missing"
        for error in response.json()["detail"]
    )


@pytest.fixture
def loaded_model_case(monkeypatch, tmp_path, valid_payload):
    import json

    import joblib
    import numpy as np
    import pandas as pd
    from sklearn.linear_model import LinearRegression

    from bike_demand.validate import FEATURES

    features = list(FEATURES)
    training_frame = pd.DataFrame(np.eye(len(features)), columns=features)
    targets = np.arange(1, len(features) + 1, dtype=float)

    # This small model is a test fixture, not the evaluated baseline.
    model = LinearRegression(fit_intercept=False).fit(training_frame, targets)

    model_path = tmp_path / "model.joblib"
    metadata_path = tmp_path / "model-metadata.json"
    version = f"test-artifact-{tmp_path.name}"

    joblib.dump(model, model_path)
    metadata_path.write_text(
        json.dumps({"model_version": version, "features": features}),
        encoding="utf-8",
    )

    payload = {
        **valid_payload,
        "season": 3,
        "yr": 1,
        "mnth": 7,
        "hr": 15,
        "holiday": 0,
    }
    frame = pd.DataFrame([payload], columns=features)
    expected = float(model.predict(frame)[0])
    assert expected >= 0

    monkeypatch.setenv("MODEL_PATH", str(model_path))
    monkeypatch.setenv("METADATA_PATH", str(metadata_path))

    with TestClient(api.app) as client:
        yield client, payload, version, expected


def test_health_reports_loaded_model_version(loaded_model_case):
    client, _, version, _ = loaded_model_case
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["model_version"] == version


def test_predict_reports_loaded_model_version(loaded_model_case):
    client, payload, version, _ = loaded_model_case
    response = client.post("/predict", json=payload)

    assert response.status_code == 200
    assert response.json()["model_version"] == version


@pytest.mark.regression
def test_prediction_matches_saved_model(loaded_model_case):
    import math

    client, payload, _, expected = loaded_model_case
    response = client.post("/predict", json=payload)

    assert response.status_code == 200
    prediction = response.json()["prediction"]
    assert isinstance(prediction, (int, float))
    assert not isinstance(prediction, bool)
    assert math.isfinite(prediction)
    assert prediction >= 0
    assert prediction == pytest.approx(expected)

def test_predict_rejects_invalid_hour(client_without_model):
    bad_data = {
        "season": 1, "yr": 0, "mnth": 1, "hr": 24, 
        "holiday": 0, "weekday": 0, "workingday": 0, "weathersit": 1, 
        "temp": 0.5, "atemp": 0.5, "hum": 0.5, "windspeed": 0.5
    }
    response = client_without_model.post("/predict", json=bad_data)
    assert response.status_code == 422