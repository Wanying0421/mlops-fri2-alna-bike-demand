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
