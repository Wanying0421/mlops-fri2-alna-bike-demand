from bike_demand.gate import evaluate_quality_gate


def test_gate_eligible():
    candidate = {"mae": 9.5}
    incumbent = {"mae": 10.0}
    outcome, reasons = evaluate_quality_gate(
        candidate, incumbent, provenance_valid=True
    )
    assert outcome == "Eligible"


def test_gate_rejected():
    candidate = {"mae": 11.5}
    incumbent = {"mae": 10.0}
    outcome, reasons = evaluate_quality_gate(
        candidate, incumbent, provenance_valid=True
    )
    assert outcome == "Rejected"
    assert any("exceeds incumbent threshold" in r for r in reasons)


def test_gate_blocked_missing_provenance():
    candidate = {"mae": 9.0}
    incumbent = {"mae": 10.0}
    outcome, reasons = evaluate_quality_gate(
        candidate, incumbent, provenance_valid=False
    )
    assert outcome == "Blocked/Error"


def test_gate_blocked_invalid_metric():
    candidate = {"mae": float("nan")}
    incumbent = {"mae": 10.0}
    outcome, reasons = evaluate_quality_gate(
        candidate, incumbent, provenance_valid=True
    )
    assert outcome == "Blocked/Error"
