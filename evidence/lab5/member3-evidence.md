# Lab 5 - Member 3: External deployment checks

## Current status

Local external validation completed on 2026-10-24. The checker passed against a
running Docker container with the real Lab 4 model and returned exit code 1 for
each deliberately incorrect expected identity. No model was retrained.

A teammate supplied `model.joblib` and its matching `model-metadata.json`, and
confirmed the approved model version as `baseline-02591234b64c` before the HTTP
checks. Both files were placed in the local `artifacts` directory and mounted
read-only into the container. The earlier missing-model blocker is resolved.

This evidence covers the local Docker service. The final Cloud Run deployment
must be checked separately using its URL and its own approved image source SHA.

## Code and image identity

| Item | Observed value |
| --- | --- |
| Source commit | `0c77d36b224f5fe899b2d18c90f9d6a1b8a1c463` |
| Branch | `lab-05-deployment-check` |
| Image tag | `alna-lab5-check:local` |
| Image ID reported by Docker | `sha256:a49ada5c8f79f0b5656adae31646d5a067a51f0ee59648e4ef1f4614fd2935e0` |
| Image revision label | `0c77d36b224f5fe899b2d18c90f9d6a1b8a1c463` |
| Approved model version | `baseline-02591234b64c` |
| Model-test container | `alna-lab5-model` |
| Model-test host address | `http://127.0.0.1:8003` |
| Container port | `8000` |
| Earlier missing-model container | `alna-lab5-no-model` |
| Earlier missing-model host address | `http://127.0.0.1:8001` |

The image revision label, runtime `git_sha` responses, and expected SHA matched
the source commit above. Later commits that add evidence do not change this
existing image's identity. `model-container-identity.txt` records the running
container's image identity and loopback port binding.

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

The API test result was observed in terminal output; its raw terminal output was
not saved. Those regression tests are separate from the external checks below.

### External checks with the real model

The checker ran in Windows PowerShell on the host and called the published port
of the Docker container over HTTP.

| Scenario | Observed checks | Overall result | Exit code |
| --- | --- | --- | --- |
| Approved model version and image source SHA | All checks passed | PASS | 0 |
| Only expected model version changed to `incorrect-version` | Both endpoints reported the approved version; exactly two version checks failed | FAIL, as intended | 1 |
| Approved version restored; only expected SHA changed to 40 zeros | Both endpoints reported the image source SHA; exactly two SHA checks failed | FAIL, as intended | 1 |

In all three runs, `/health` returned HTTP 200 with `status=healthy`, valid
`/predict` input returned HTTP 200 with a finite non-negative prediction, and
`hr=24` was rejected with HTTP 422 identifying the `hr` field. The valid
prediction was `168.43515450291122`.

The negative runs changed only the checker's expectation. The service continued
to answer successfully, while the checker rejected the mismatched identity.
The three captured outputs include the independently observed process exit codes.

## Commands used

These commands were run from the repository root in Windows PowerShell.

### Image build, regression tests, and earlier readiness failure

At build time, `HEAD` was the source commit `0c77d36` shown above. The following
records that build; a future build from different code needs its own source SHA.
The first container was deliberately started without a model mount.

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

### Start the service with the supplied model

Port 8002 was occupied by an older Lab 4 container. The failed new container was
removed and recreated with the following loopback binding on port 8003.

```powershell
docker run -d --name alna-lab5-model `
  -p 127.0.0.1:8003:8000 `
  --mount "type=bind,source=$($PWD.Path)\artifacts,target=/app/artifacts,readonly" `
  -e MODEL_PATH=/app/artifacts/model.joblib `
  -e METADATA_PATH=/app/artifacts/model-metadata.json `
  -e GIT_SHA=0c77d36b224f5fe899b2d18c90f9d6a1b8a1c463 `
  alna-lab5-check:local
```

The explicit SHA here belongs to this existing image. For another deployment,
the image owner must supply the actual source SHA of that image.

### Check the approved identity

```powershell
python .\check_deploy.py `
  --base-url http://127.0.0.1:8003 `
  --expected-model-version baseline-02591234b64c `
  --expected-git-sha 0c77d36b224f5fe899b2d18c90f9d6a1b8a1c463 |
  Tee-Object -FilePath .\evidence\lab5\check-expected-identity.txt
"Exit code: $LASTEXITCODE" | Tee-Object -FilePath .\evidence\lab5\check-expected-identity.txt -Append
```

Observed result: `PASS`, zero failed checks, process exit code `0`.

### Deliberately mismatch only the expected model version

```powershell
python .\check_deploy.py `
  --base-url http://127.0.0.1:8003 `
  --expected-model-version incorrect-version `
  --expected-git-sha 0c77d36b224f5fe899b2d18c90f9d6a1b8a1c463 |
  Tee-Object -FilePath .\evidence\lab5\check-model-version-mismatch.txt
"Exit code: $LASTEXITCODE" | Tee-Object -FilePath .\evidence\lab5\check-model-version-mismatch.txt -Append
```

Observed result: `FAIL`, two failed model-version checks, process exit code `1`.

### Deliberately mismatch only the expected Git SHA

```powershell
python .\check_deploy.py `
  --base-url http://127.0.0.1:8003 `
  --expected-model-version baseline-02591234b64c `
  --expected-git-sha 0000000000000000000000000000000000000000 |
  Tee-Object -FilePath .\evidence\lab5\check-git-sha-mismatch.txt
"Exit code: $LASTEXITCODE" | Tee-Object -FilePath .\evidence\lab5\check-git-sha-mismatch.txt -Append
```

Observed result: `FAIL`, two failed SHA checks, process exit code `1`. The all-zero
value has valid 40-character SHA syntax, so this is a deployment-check failure,
not a command-line validation error.

### Capture the running container

```powershell
cmd /c "docker logs alna-lab5-model > evidence\lab5\model-container.log 2>&1"
docker inspect alna-lab5-model --format '{{.Name}} {{.Image}} {{json .Config.Labels}} {{json .NetworkSettings.Ports}}' | Tee-Object -FilePath .\evidence\lab5\model-container-identity.txt
```

The log capture uses `cmd` redirection to preserve stdout and stderr without
PowerShell's native-error formatting. The saved logs show application startup
and three groups of HTTP 200, 200, and 422 responses, matching the checker runs.

## Raw evidence

Keep this document in `evidence/lab5` with these files:

- [Image identity](image-identity.txt): image ID and source-revision label.
- [Missing-model HTTP response](missing-model-health.txt): response headers and
  JSON error body from the host request.
- [Missing-model container logs](missing-model-container.log): captured container
  output for the failure run.
- [Approved-identity check](check-expected-identity.txt): successful external
  checks and process exit code 0.
- [Model-version mismatch](check-model-version-mismatch.txt): expected versus
  observed versions and process exit code 1.
- [Git-SHA mismatch](check-git-sha-mismatch.txt): expected versus observed SHAs
  and process exit code 1.
- [Model-container logs](model-container.log): startup and request status logs
  from the real-model container.
- [Model-container identity](model-container-identity.txt): image ID, revision
  label, source URL, and published loopback port.

The earlier missing-model failure demonstrates that the service refuses to
report readiness when its model is unavailable. The later checker runs establish
valid prediction behavior and identity comparisons with the real model. These
captured container logs are Uvicorn/startup logs; structured JSON request logging
will be assessed when Member 2's changes are integrated.

## Remaining validation and handover

1. Commit these new evidence files and this updated document to the Member 3
   branch, then update the existing pull request for review.
2. Give the working check command to the README owner. Expected identities must
   remain independent of the service response.
3. After team integration, the deployment owner runs the checker against the
   final live service URL using the approved model version and the final image's
   source SHA, and records that deployment's results separately.

Cloud Run verification, structured-logging integration, and PR review/merge are
team follow-up work. This document does not claim a successful live cloud check,
a passing remote CI run, or a merged pull request.
