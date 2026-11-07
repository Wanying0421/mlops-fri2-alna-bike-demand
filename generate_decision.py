import hashlib
import json
from pathlib import Path

from bike_demand.gate import evaluate_quality_gate


def get_policy_version():
    policy_path = Path("src/bike_demand/gate.py")
    if policy_path.exists():
        content = policy_path.read_bytes()
        return hashlib.sha256(content).hexdigest()[:12]
    return "unknown"


def create_decision_record():
    training_dir = Path("evidence/lab7/training")
    bundles = list(training_dir.glob("candidate-*")) if training_dir.exists() else []

    metadata_exists = False
    metadata = {}

    if not bundles:
        outcome, reasons = evaluate_quality_gate({}, {}, provenance_valid=False)
    else:
        latest_bundle = sorted(bundles)[-1]
        metadata_path = latest_bundle / "model-metadata.json"
        if not metadata_path.exists():
            outcome, reasons = evaluate_quality_gate({}, {}, provenance_valid=False)
        else:
            metadata_exists = True
            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            status = metadata.get("status", "evaluated")
            if status == "not_evaluated":
                outcome, reasons = (
                    "Blocked/Error",
                    ["Candidate model status is not_evaluated."],
                )
            else:
                candidate_metrics = {"mae": metadata.get("metrics", {}).get("mae")}
                incumbent_metrics = {"mae": 10.0}
                outcome, reasons = evaluate_quality_gate(
                    candidate_metrics, incumbent_metrics, provenance_valid=True
                )

    record = {
        "policy_version": get_policy_version(),
        "candidate_identity": metadata.get("model_id", "missing")
        if metadata_exists
        else "missing",
        "incumbent_identity": "bike-demand-incumbent-baseline",
        "outcome": outcome,
        "reasons": reasons,
    }

    Path("evidence").mkdir(exist_ok=True)
    with open("evidence/decision_record.json", "w") as f:
        json.dump(record, f, indent=2)
    print(f"Decision record generated: {outcome}")


if __name__ == "__main__":
    create_decision_record()
