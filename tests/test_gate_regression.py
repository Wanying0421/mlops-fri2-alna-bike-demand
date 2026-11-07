from bike_demand.gate import evaluate_quality_gate


def test_missing_evidence_blocks():
    outcome, reasons = evaluate_quality_gate({}, {}, provenance_valid=False)
    assert outcome == "Blocked/Error"
    assert any("missing or invalid" in r.lower() for r in reasons)


def test_exceeding_mae_rejects():
    outcome, reasons = evaluate_quality_gate(
        {"mae": 11.0}, {"mae": 10.0}, provenance_valid=True
    )
    assert outcome == "Rejected"


def test_eligible_candidate_passes():
    outcome, reasons = evaluate_quality_gate(
        {"mae": 8.5}, {"mae": 10.0}, provenance_valid=True
    )
    assert outcome == "Eligible"
