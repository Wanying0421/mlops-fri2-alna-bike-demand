#!/usr/bin/env python3
"""Check the deployed Bike Demand API from outside its container.

Supply the approved model version and the full Git SHA of the image's source
commit. Never obtain the expected identities from the API being checked.

Exit codes: 0 = all checks passed, 1 = a deployment check failed,
2 = invalid command-line arguments.
"""

import argparse
import json
import math
import re
import sys
from http.client import HTTPException
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


VALID_INPUT = {
    "season": 2,
    "mnth": 6,
    "holiday": 0,
    "yr": 1,
    "hr": 12,
    "weekday": 3,
    "workingday": 1,
    "weathersit": 1,
    "temp": 0.6,
    "atemp": 0.6,
    "hum": 0.5,
    "windspeed": 0.2,
}


class CheckError(Exception):
    """A request could not provide a usable JSON response."""


def base_url_arg(value: str) -> str:
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError as error:
        raise argparse.ArgumentTypeError("Invalid base URL.") from error
    if (
        parts.scheme not in {"http", "https"}
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
        or parts.query
        or parts.fragment
        or port == 0
    ):
        raise argparse.ArgumentTypeError(
            "Use an HTTP(S) base URL without credentials, query or fragment."
        )
    return value.rstrip("/")


def git_sha_arg(value: str) -> str:
    if not re.fullmatch(r"[0-9a-fA-F]{40}", value):
        raise argparse.ArgumentTypeError("Use the full 40-character Git SHA.")
    return value.lower()


def timeout_arg(value: str) -> float:
    try:
        seconds = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Timeout must be a number.") from error
    if not math.isfinite(seconds) or seconds <= 0:
        raise argparse.ArgumentTypeError("Timeout must be finite and positive.")
    return seconds


def request_json(
    url: str, method: str, payload: dict | None, timeout: float
) -> tuple[int, Any]:
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, headers=headers, method=method)

    try:
        with urlopen(request, timeout=timeout) as response:
            status = response.status
            body = response.read()
    except HTTPError as error:
        # An expected validation error is still a response we need to inspect.
        with error:
            status = error.code
            body = error.read()
    except (URLError, OSError, HTTPException, ValueError) as error:
        raise CheckError(f"Network request failed: {error}") from error

    try:
        return status, json.loads(body)
    except (ValueError, UnicodeDecodeError) as error:
        raise CheckError(f"HTTP {status}: response is not valid JSON.") from error


class Results:
    def __init__(self) -> None:
        self.failures = 0

    def check(self, label: str, passed: bool, expected: Any, observed: Any) -> None:
        outcome = "PASS" if passed else "FAIL"
        self.failures += int(not passed)
        print(
            f"[{outcome}] {label}: "
            f"expected={json.dumps(expected)} observed={json.dumps(observed)}"
        )

    def response(
        self,
        args: argparse.Namespace,
        label: str,
        method: str,
        path: str,
        payload: dict | None,
        expected_status: int,
    ) -> dict | None:
        try:
            status, body = request_json(
                args.base_url + path, method, payload, args.timeout
            )
        except CheckError as error:
            self.check(label, False, "a JSON HTTP response", str(error))
            return None
        self.check(
            f"{label} HTTP status", status == expected_status, expected_status, status
        )
        if status != expected_status:
            return None
        self.check(
            f"{label} JSON body", isinstance(body, dict), "object", type(body).__name__
        )
        return body if isinstance(body, dict) else None

    def identity(self, label: str, body: dict, args: argparse.Namespace) -> None:
        version = body.get("model_version")
        self.check(
            f"{label} model_version",
            version == args.expected_model_version,
            args.expected_model_version,
            version,
        )
        revision = body.get("git_sha")
        matches = (
            isinstance(revision, str)
            and re.fullmatch(r"[0-9a-fA-F]{40}", revision) is not None
            and revision.lower() == args.expected_git_sha
        )
        self.check(f"{label} git_sha", matches, args.expected_git_sha, revision)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, type=base_url_arg)
    parser.add_argument("--expected-model-version", required=True)
    parser.add_argument("--expected-git-sha", required=True, type=git_sha_arg)
    parser.add_argument(
        "--timeout",
        type=timeout_arg,
        default=30.0,
        help="Timeout per request in seconds (default: 30).",
    )
    args = parser.parse_args()
    if not args.expected_model_version.strip():
        parser.error("The expected model version must not be empty.")

    results = Results()
    health = results.response(args, "GET /health", "GET", "/health", None, 200)
    if health is not None:
        results.check(
            "GET /health readiness",
            health.get("status") == "healthy",
            "healthy",
            health.get("status"),
        )
        results.identity("GET /health", health, args)

    prediction = results.response(
        args, "POST /predict valid input", "POST", "/predict", VALID_INPUT, 200
    )
    if prediction is not None:
        results.identity("POST /predict", prediction, args)
        value = prediction.get("prediction")
        valid_number = isinstance(value, (int, float)) and not isinstance(value, bool)
        if valid_number:
            try:
                valid_number = math.isfinite(value) and value >= 0
            except OverflowError:
                valid_number = False
        results.check(
            "POST /predict prediction",
            valid_number,
            "a finite non-negative number",
            value,
        )

    # Change only the hour so that the invalid case has a valid control.
    invalid_input = {**VALID_INPUT, "hr": 24}
    rejection = results.response(
        args, "POST /predict hr=24", "POST", "/predict", invalid_input, 422
    )
    if rejection is not None:
        details = rejection.get("detail")
        hour_rejected = isinstance(details, list) and any(
            isinstance(item, dict)
            and isinstance(item.get("loc"), list)
            and item["loc"] == ["body", "hr"]
            for item in details
        )
        results.check(
            "POST /predict validation",
            hour_rejected,
            "validation error on hr",
            "hr rejected" if hour_rejected else "missing hr validation error",
        )

    exit_code = 1 if results.failures else 0
    print(
        f"RESULT: {'FAIL' if exit_code else 'PASS'}; "
        f"failed checks={results.failures}; exit code={exit_code}"
    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
