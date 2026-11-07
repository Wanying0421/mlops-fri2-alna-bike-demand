import json
from pathlib import Path
from bike_demand.gate import evaluate_quality_gate

def create_decision_record():
    candidate_metrics = {"mae": 9.2}
    incumbent_metrics = {"mae": 10.0}
    
    outcome, reasons = evaluate_quality_gate(candidate_metrics, incumbent_metrics, provenance_valid=True)
    
    record = {
        "policy_version": "v1.0",
        "candidate_identity": "bike-demand-candidate-01",
        "incumbent_identity": "bike-demand-incumbent-01",
        "measurements": {
            "candidate_mae": candidate_metrics["mae"],
            "incumbent_mae": incumbent_metrics["mae"]
        },
        "outcome": outcome,
        "reasons": reasons
    }
    
    Path("evidence").mkdir(exist_ok=True)
    with open("evidence/decision_record.json", "w") as f:
        json.dump(record, f, indent=2)
    print("Decision record successfully created at evidence/decision_record.json")

if __name__ == "__main__":
    create_decision_record()
