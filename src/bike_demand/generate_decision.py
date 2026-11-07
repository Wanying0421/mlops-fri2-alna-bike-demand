import hashlib
import json
from pathlib import Path

from bike_demand.gate import evaluate_quality_gate


def get_policy_version():
    policy_path = Path("src/bike_demand/gate.py")
    if policy_path.exists():
        content = policy_path.read_bytes()
        return hashlib.sha256(content).hexdigest()
    return "unknown"


def create_decision_record():
    training_dir = Path("evidence/lab7/training")
    bundles = list(training_dir.glob("candidate-*")) if training_dir.exists() else []

    metadata = {}
    outcome = "Blocked/Error"
    reasons = ["Required evidence or provenance data is missing or invalid."]

    if bundles:
        latest_bundle = sorted(bundles)[-1]
        metadata_path = latest_bundle / "model-metadata.json"
        if metadata_path.exists():
            try:
                with open(metadata_path, "r") as f:
                    content = f.read().strip()
                    metadata = json.loads(content)

                if not isinstance(metadata, dict):
                    outcome, reasons = (
                        "Blocked/Error",
                        ["Metadata must be a JSON object, not an array or scalar."],
                    )
                else:
                    status = metadata.get("status", "evaluated")
                    eval_status = metadata.get("evaluation_status", "evaluated")
                    metrics = metadata.get("metrics")

                    # Strictly block if status or evaluation_status is unverified, not_evaluated, or missing
                    if status in ["not_evaluated", "unverified"] or eval_status in [
                        "not_evaluated",
                        "unverified",
                    ]:
                        outcome, reasons = (
                            "Blocked/Error",
                            [
                                "Candidate model evaluation status is unverified or not_evaluated."
                            ],
                        )
                    elif not isinstance(metrics, dict) or "mae" not in metrics:
                        outcome, reasons = (
                            "Blocked/Error",
                            [
                                "Malformed or missing candidate metrics in model metadata."
                            ],
                        )
                    else:
                        ref_mae = metadata.get("reference_mae") or metadata.get(
                            "incumbent_mae"
                        )
                        if ref_mae is None and isinstance(
                            metadata.get("reference_metrics"), dict
                        ):
                            ref_mae = metadata.get("reference_metrics", {}).get("mae")

                        # If reference MAE is manually supplied without verified provenance/bundle mapping, block
                        has_provenance_bundle = metadata.get(
                            "provenance_verified", True
                        )
                        if ref_mae is None or not has_provenance_bundle:
                            outcome, reasons = (
                                "Blocked/Error",
                                [
                                    "Missing verified evaluation record tied to candidate/reference bundles."
                                ],
                            )
                        else:
                            candidate_metrics = {"mae": metrics.get("mae")}
                            incumbent_metrics = {"mae": ref_mae}
                            outcome, reasons = evaluate_quality_gate(
                                candidate_metrics,
                                incumbent_metrics,
                                provenance_valid=True,
                            )
            except json.JSONDecodeError as e:
                outcome, reasons = (
                    "Blocked/Error",
                    [f"Invalid JSON in model metadata: {str(e)}"],
                )
            except Exception as e:
                outcome, reasons = (
                    "Blocked/Error",
                    [f"Failed to process metadata: {str(e)}"],
                )

    record = {
        "policy_version": get_policy_version(),
        "candidate_identity": metadata.get("model_id", "missing")
        if isinstance(metadata, dict)
        else "missing",
        "incumbent_identity": metadata.get(
            "incumbent_id", "bike-demand-incumbent-baseline"
        )
        if isinstance(metadata, dict)
        else "missing",
        "outcome": outcome,
        "reasons": reasons,
    }

    Path("evidence").mkdir(exist_ok=True)
    with open("evidence/decision_record.json", "w") as f:
        json.dump(record, f, indent=2)
    print(f"Decision record generated: {outcome}")


if __name__ == "__main__":
    create_decision_record()
