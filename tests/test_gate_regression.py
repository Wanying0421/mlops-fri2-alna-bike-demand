import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json

import generate_decision
from bike_demand.gate import evaluate_quality_gate


def test_missing_evidence_blocks():
    outcome, reasons = evaluate_quality_gate({}, {}, provenance_valid=False)
    assert outcome == "Blocked/Error"


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


def test_generator_blocks_partial_metadata(tmp_path, monkeypatch):
    training_dir = tmp_path / "evidence" / "lab7" / "training" / "candidate-test"
    training_dir.mkdir(parents=True)
    meta_file = training_dir / "model-metadata.json"
    meta_file.write_text(json.dumps({"metrics": {"mae": 9.0}}))

    monkeypatch.chdir(tmp_path)
    generate_decision.create_decision_record()

    decision_file = tmp_path / "evidence" / "decision_record.json"
    assert decision_file.exists()
    data = json.loads(decision_file.read_text())
    assert data["outcome"] == "Blocked/Error"


def test_generator_blocks_json_array(tmp_path, monkeypatch):
    training_dir = tmp_path / "evidence" / "lab7" / "training" / "candidate-test"
    training_dir.mkdir(parents=True)
    meta_file = training_dir / "model-metadata.json"
    meta_file.write_text(json.dumps([]))

    monkeypatch.chdir(tmp_path)
    generate_decision.create_decision_record()

    decision_file = tmp_path / "evidence" / "decision_record.json"
    assert decision_file.exists()
    data = json.loads(decision_file.read_text())
    assert data["outcome"] == "Blocked/Error"
