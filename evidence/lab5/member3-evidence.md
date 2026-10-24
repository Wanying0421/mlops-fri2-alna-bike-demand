# Lab 5 - Member 3: External deployment checks

## Current status

Local validation is partially complete. The image builds, the existing API tests
pass, and an HTTP request from the host confirms that a container without a
loaded model returns HTTP 503.

The next step is to run `check_deploy.py` against the real Lab 4 model. The local
`artifacts` directory was empty, and the project search did not find a model
artifact or its metadata. A teammate needs to provide the matching
`model.joblib` and `model-metadata.json` files used for Lab 4.

## Code and image identity

| Item | Observed value |
| --- | --- |
| Source commit | `0c77d36b224f5fe899b2d18c90f9d6a1b8a1c463` |
| Branch | `lab-05-deployment-check` |
| Image tag | `alna-lab5-check:local` |
| Image ID reported by Docker | `sha256:a49ada5c8f79f0b5656adae31646d5a067a51f0ee59648e4ef1f4614fd2935e0` |
| Image revision label | `0c77d36b224f5fe899b2d18c90f9d6a1b8a1c463` |
| Failure-test container | `alna-lab5-no-model` |
| Host address | `http://127.0.0.1:8001` |
| Container port | `8000` |

The source commit above identifies the image used for these observations.
Later commits that add evidence do not change this existing image's identity.

## Implementation

- `check_deploy.py` sends real HTTP requests from outside the service container.
- Both `/health` and `/predict` expose `git_sha`, read from `GIT_SHA`, alongside
  the existing response fields. An unset value is reported as `unknown`.
- The checker compares both endpoints' `model_version` and full `git_sha` with
  explicit expected values supplied on its command line.
- It checks readiness, a finite non-negative prediction, and rejection of
  `hr=24` with HTTP 422 and an error identifying the `hr` field.
- Its exit codes are 0 for a successful check, 1 for a failed deployment check,
  and 2 for invalid command-line arguments.
- It uses the Python standard library.

Expected values must come from the approved artifact metadata and the intended
image's source commit. Reading expected identities back from the service under
test would not provide an independent check. The image owner must set `GIT_SHA`
to the commit actually used to build the image.

## Observed local checks

| Check | Observed result |
| --- | --- |
| `python check_deploy.py --help` | CLI options displayed successfully |
| `git diff --check`, after whitespace cleanup | No errors reported |
| Docker build | All 21 build steps completed |
| Existing API test suite inside the image | 24 tests passed in 6.58 seconds |
| Host HTTP request to `/health`, without a model | HTTP 503, `Service unavailable: Model not loaded` |

The API test result was observed in terminal output. The raw evidence files below
record the image identity, the missing-model HTTP response, and container logs.

## Commands used

These commands were run from the repository root in Windows PowerShell. The
container was deliberately started without a model mount for the failure case.

```powershell
$deploySha = (git rev-parse HEAD).Trim()
docker build --build-arg "VCS_REF=$deploySha" -t alna-lab5-check:local .

docker run --rm alna-lab5-check:local uv run --locked pytest -q tests/test_api.py
docker image inspect alna-lab5-check:local --format '{{.Id}}'

docker run -d --name alna-lab5-no-model -p 127.0.0.1:8001:8000 -e "GIT_SHA=$deploySha" alna-lab5-check:local

New-Item -ItemType Directory -Force .\evidence\lab5 | Out-Null
curl.exe -sS -i --max-time 30 --output .\evidence\lab5\missing-model-health.txt --write-out "HTTP status: %{http_code}\n" http://127.0.0.1:8001/health

docker logs alna-lab5-no-model 2>&1 | Set-Content -Encoding utf8 .\evidence\lab5\missing-model-container.log
docker image inspect alna-lab5-check:local --format '{{.Id}} {{json .Config.Labels}}' | Set-Content -Encoding utf8 .\evidence\lab5\image-identity.txt
```

## Raw evidence

Keep this document in `evidence/lab5` with these files:

- [Image identity](image-identity.txt): image ID and source-revision label.
- [Missing-model HTTP response](missing-model-health.txt): response headers and
  JSON error body from the host request.
- [Missing-model container logs](missing-model-container.log): captured container
  output for the failure run.

The failure demonstrates that the service refuses to report readiness when its
model is unavailable. It does not establish a successful prediction or matching
runtime model/code identities.

## Remaining validation and handover

1. Obtain the real Lab 4 model and its matching metadata, including the approved
   model version.
2. Start a container with those files mounted read-only and the correct
   `MODEL_PATH`, `METADATA_PATH`, and `GIT_SHA` settings.
3. Run `check_deploy.py` from the host with the approved version and image source
   SHA. Record its output and exit code 0.
4. Change only the expected model version and verify exit code 1. Restore it,
   change only the expected SHA to a different valid 40-character SHA, and verify
   exit code 1 again. Save both outputs.
5. Record the final container's logs and identity, and add the exact working check
   command to the team's deployment instructions.
6. Open the Member 3 pull request for review. If the model is still unavailable,
   use a draft and retain the explicit blocker above.

The owner of the final deployment can run the same checker against its live
service URL with the final approved model version and deployed image source SHA.
