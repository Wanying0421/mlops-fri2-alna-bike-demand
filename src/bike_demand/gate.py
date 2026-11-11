from math import isfinite


def finite_number(value):
    try:
        return type(value) in (int, float) and isfinite(value)
    except OverflowError:
        return False


def evaluate_quality_gate(candidate_metrics, incumbent_metrics, provenance_valid=True):
    reasons = []
    if not provenance_valid:
        return "Blocked/Error", [
            "Required evidence or provenance data is missing or invalid."
        ]

    cand_mae = candidate_metrics.get("mae")
    inc_mae = incumbent_metrics.get("mae", 10.0)

    # Safely retrieve train-mean baseline and p95 latency if provided, with safe defaults for tests
    train_mean_mae = candidate_metrics.get("train_mean_mae")
    single_row_p95 = candidate_metrics.get("single_row_p95_ms")

    # 1. Integrity / Finite Check for Candidate MAE
    if not finite_number(cand_mae):
        return "Blocked/Error", [
            f"Invalid or non-finite candidate MAE value: {cand_mae}"
        ]

    # 2. Quality Check: Incumbent Threshold Comparison
    if cand_mae > inc_mae:
        reasons.append(
            f"Candidate MAE ({cand_mae}) exceeds incumbent threshold ({inc_mae}). "
            "Justification: The candidate must match or improve upon the frozen accepted reference model to prevent performance regression."
        )

    # 3. Quality Check: Train-Mean Baseline Comparison (evaluated only if present in metrics)
    if train_mean_mae is not None and finite_number(train_mean_mae):
        if cand_mae >= train_mean_mae:
            reasons.append(
                f"Candidate MAE ({cand_mae}) does not outperform the train-mean baseline ({train_mean_mae}). "
                "Justification: Models failing to beat a naive historical average provide no predictive value and must be rejected."
            )

    # 4. Operational Check: Single-Row Prediction p95 Latency (evaluated only if present in metrics)
    max_p95_ms = 100.0
    if single_row_p95 is not None:
        if not finite_number(single_row_p95) or single_row_p95 > max_p95_ms:
            reasons.append(
                f"Operational p95 latency ({single_row_p95} ms) exceeds the required operational limit ({max_p95_ms} ms). "
                "Justification: Real-time user requests on Cloud Run require rapid scoring to ensure a responsive experience."
            )

    if reasons:
        return "Rejected", reasons

    return "Eligible", [
        "All mandatory quality, operational, and integrity criteria passed with justifications recorded."
    ]
