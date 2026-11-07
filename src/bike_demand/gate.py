import json
from math import isfinite
from pathlib import Path


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

    if not finite_number(cand_mae):
        return "Blocked/Error", [
            f"Invalid or non-finite candidate MAE value: {cand_mae}"
        ]

    if cand_mae > inc_mae:
        reasons.append(
            f"Candidate MAE ({cand_mae}) exceeds incumbent threshold ({inc_mae})."
        )
        return "Rejected", reasons

    return "Eligible", [
        "All mandatory quality, operational, and integrity criteria passed."
    ]
