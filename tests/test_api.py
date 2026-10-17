import pytest
from bike_demand.api import PredictRequest
from pydantic import ValidationError


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


def test_schema_accepts_valid_input(valid_payload):
    request = PredictRequest.model_validate(valid_payload)
    assert request.model_dump() == valid_payload


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("hum", 1.5),
        ("hr", "hello"),
        ("cnt", 100),
        ("casual", 10),
        ("registered", 90),
    ],
)
def test_schema_rejects_invalid_input(valid_payload, field, value):
    payload = {**valid_payload, field: value}

    with pytest.raises(ValidationError) as caught:
        PredictRequest.model_validate(payload)

    assert any(error["loc"] == (field,) for error in caught.value.errors())


def test_schema_requires_temp(valid_payload):
    valid_payload.pop("temp")

    with pytest.raises(ValidationError) as caught:
        PredictRequest.model_validate(valid_payload)

    assert any(
        error["loc"] == ("temp",) and error["type"] == "missing"
        for error in caught.value.errors()
    )


def test_schema_rejects_numeric_string(valid_payload):
    valid_payload["hr"] = "10"

    with pytest.raises(ValidationError):
        PredictRequest.model_validate(valid_payload)
