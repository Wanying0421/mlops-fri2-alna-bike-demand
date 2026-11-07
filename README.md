# Bike Demand — MLOps Project

## User + Goal

**User:** Bike-share operators who need to estimate hourly rental demand.

**Goal:** Build a service that estimates total hourly bike rentals from calendar and weather inputs, delivered as a prediction API.

## Inputs + Output

| | Description |
|---|---|
| **Inputs** | Calendar (hour, weekday, season) + supplied weather conditions |
| **Output** | `prediction` (estimated hourly rentals) + `model_version` (loaded model identity) |

## Scope + Non-Goals

**In scope:**
- Shared team repository and Git workflow
- Code quality checks (ruff, pytest)
- Peer review on every change
- Prediction API + Docker
- Data validation, chronological split, baseline comparison, MLflow tracking (Lab 2)

**Out of scope:**
- Forecasting future weather
- Station-level demand
- Real-time streaming
- Cloud deployment

  
## How Success Is Checked

- `uv run --locked ruff check .` : no lint errors
- `uv run --locked ruff format --check .` : all files formatted
- `uv run --locked pytest -q -m infra` : setup healthy
- `uv run --locked pytest -q -m lab1` : behavior contract respected
- `uv run --locked pytest -q` : all tests pass

## Lab 3 & Lab 4: Containerized Baseline, Dependency Locking & Prediction API

### Prerequisites
* Docker installed and running on your machine.
* Git for checking out the exact revision.

### Getting the Code
Clone the repository:

```Bash
git clone https://github.com/Wanying0421/mlops-fri2-alna-bike-demand.git
cd mlops-fri2-alna-bike-demand
```

### 1. Building the Docker Image
## To build the container image from a clean checkout, run the following command from the root of the repository:

```bash
docker build -t mlops-baseline:lab3 .
```
### 2. Running the API Container with a Model
## Since the Dockerfile starts the API service by default, you can provide your Lab 3 model (model.joblib) and metadata (model-metadata.json) by mounting them into the container and specifying their paths via environment variables:

```Bash
docker run --rm -p 8000:8000 -v $(pwd)/artifacts:/app/artifacts -e MODEL_PATH=/app/artifacts/model.joblib -e METADATA_PATH=/app/artifacts/model-metadata.json mlops-baseline:lab3
```
## To test the prediction endpoint against the running container, use the following curl command with all 12 required fields and correct closing quotes:

```Bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "season": 1,
    "yr": 0,
    "mnth": 1,
    "hr": 0,
    "holiday": 0,
    "weekday": 6,
    "workingday": 0,
    "weathersit": 1,
    "temp": 0.24,
    "atemp": 0.2879,
    "hum": 0.81,
    "windspeed": 0.0
  }'
```

### 3. Running the Baseline and Tests
## Run the Baseline Pipeline
## To execute the core ML baseline pipeline explicitly instead of starting the default API service:

```Bash
docker run --rm --entrypoint uv mlops-baseline:lab3 run --locked python -m bike_demand.train --config configs/baseline.yaml
```
## Run the Test Suite
## To verify that all unit and integration tests pass successfully inside the container environment:

```Bash
docker run --rm mlops-baseline:lab3 uv run --locked pytest -q
```
### 4. Verifying Dependency Locking
## To test that a stale or missing lockfile correctly halts execution rather than auto-regenerating:

```Bash
docker run --rm --entrypoint sh mlops-baseline:lab3 -c "rm uv.lock && uv sync --locked"
```
### 5. Retrieving Outputs
## To copy generated artifacts, logs, or model outputs from a container instance:

```Bash
docker run --name temp-container --entrypoint uv mlops-baseline:lab3 run --locked python -m bike_demand.train --config configs/baseline.yaml
docker cp temp-container:/app/artifacts ./out
docker rm temp-container
```

## Lab 5 : Service Deployment, Structured Logging & Model Version Checks

### Deploy & Operations

#### Part A: Running the Service

1. **Settings:** What changes between laptop and container?
   * *Choice:* Configuration and file paths are injected via environment variables (`MODEL_PATH`, `METADATA_PATH`) and runtime volume mounts rather than local relative project paths.
   * *Rejected:* Hardcoding absolute local paths inside the source code, which breaks reproducibility across different machines.
   * *Why:* Environment-based configuration ensures the exact same code runs identically in local testing, CI, and cloud environments.

2. **Model Source:** Where does the model come from at start-up?
   * *Choice:* The pre-trained model artifact (`model.joblib`) and metadata file are mounted into the container at runtime.
   * *Rejected:* Pulling models dynamically from an unversioned remote storage URL during startup.
   * *Why:* Keeps deployments deterministic and guarantees the service runs against a verified, version-controlled artifact.

3. **Readiness:** When do you call the service "ready"?
   * *Choice:* When Uvicorn finishes startup and the `/health` endpoint returns a `200 OK` status with a loaded model version.
   * *Rejected:* Considering the container ready the moment the process container ID is spawned.
   * *Why:* Process start does not guarantee model deserialization; verifying `/health` ensures the model is actually loaded into memory and ready to serve requests.

4. **Failure Mode:** What does it say if the model is missing?
   * *Choice:* The application fails honestly by returning a `503 Service Unavailable: Model not loaded` response.
   * *Rejected:* Catching the error silently and returning dummy or zero predictions.
   * *Why:* Failing fast and explicitly prevents silent prediction corruption and ensures operators immediately detect missing assets.

5. **Log Line:** What must one request tell an operator?
   * *Choice:* Every request outputs a structured event log line containing the endpoint path, response status code, execution duration, and active model version.
   * *Rejected:* Relying on unstructured print statements or default server access logs.
   * *Why:* Structured logs allow automated monitoring tools and operators to parse request patterns and debug failures instantly.

#### Part B: Evidence & Verification

6. **Secrets:** What must never appear in a log?
   * *Choice:* API keys, passwords, database credentials, personal user data, and raw feature vectors containing sensitive metadata.
   * *Rejected:* Logging full incoming HTTP request payloads for debugging.
   * *Why:* Protects user privacy and security compliance, preventing sensitive information leaks into stdout log aggregators.

7. **Identity:** Which ID shows which model is running?
   * *Choice:* The `model_version` string and the `model_sha256` checksum hash returned by the `/health` endpoint.
   * *Rejected:* Relying solely on the Git commit hash of the code repository.
   * *Why:* Code version changes independently from model training data versions; verifying the model hash proves *which exact model weights* are answering requests.

8. **Expected Model:** Who knows the expected model, and when?
   * *Choice:* The integration team and the validation test scripts know the expected version prior to deployment through metadata tracking records.
   * *Rejected:* Discovering the active model only after observing live traffic drift.
   * *Why:* Strict version alignment prevents unauthorized or unverified model weight replacements in production.

9. **Deployment Promise:** What does "deployed" promise to others?
   * *Choice:* That the service is fully containerized, responds reliably over the network interface via standard API contracts, and executes under a verified runtime state.
   * *Rejected:* Claiming deployment success simply because unit tests passed on a developer's laptop.
   * *Why:* Guarantees reproducibility and operational trust for external consumers and stakeholders.

10. **Break It:** What does an intentional failure leave behind?
    * *Choice:* Triggering an invalid request or removing the model file leaves behind a clear `422 Unprocessable Entity` or `503` error status code alongside corresponding structured error traces in `docker logs`.
    * *Rejected:* Crashing the container with zero logging output.
    * *Why:* Validates that failure modes are observable, predictable, and understandable to a stranger or system operator.

## Lab 6 — CI

### What runs and what is required to merge

`.github/workflows/ci.yml` defines `Lab 6 CI` with two ordered jobs:

1. **Checks:** install from `uv.lock`, check Ruff lint and formatting, run the
   preflight, then run `uv run --locked pytest -q` with a JUnit report.
   This includes all tests discovered under `tests/`: infrastructure, team
   helpers, data/split/baseline exercises and the API. The starting snapshot
   contains 73 tests; new tests are discovered automatically.
2. **Container:** after Checks succeeds, make a synthetic model fixture, build
   the Docker image from the checked revision, run the complete suite in that
   image, start its API, then run `check_deploy.py` from the runner over HTTP.
   The expected model version and Git SHA are supplied before the API is called.

Both jobs must be green on the revision being merged. Team review still controls
the manual merge, including when the repository plan cannot enforce required
checks through branch protection.

### Reading the original workflow

The previous workflow already ran on pushes to `main`, PRs targeting `main`, and
manual dispatch. It used Ubuntu 24.04, a 15-minute limit, `contents: read`,
disabled persisted checkout credentials and locked uv commands. It ran the
preflight, Ruff, and only the `infra` and `lab1` pytest selections. It did not run
the exercise/API tests or build a container. `checkout@v6` was a movable tag.

The revised workflow keeps the safe setup and the existing uv version/pin,
pins checkout and artifact upload to full commit SHAs, and runs the whole suite.
`--strict-markers --strict-config` are already enabled in `pyproject.toml`.
There are no test-selection filters, allowed failures, or retries of failing
tests. The readiness wait only retries startup HTTP probes for a bounded time.

### A model that a clean runner can actually obtain

`artifacts/` is ignored by Git. The Dockerfile copies it, so a fresh checkout
does not have the files needed for that COPY instruction.

The Container job runs `ci/create_smoke_model.py` before the build. It creates a
tiny constant model from synthetic input, with version `ci-smoke-<checked SHA>`.
The helper refuses to overwrite a non-empty output directory. No dependency or
lock file is changed, and no training or evaluation uses the course dataset.

This image checks packaging, test execution, startup, HTTP validation and model/
code identity. Its fixture is **not** the evaluated Lab 4 model, a deployable
release candidate, or evidence of model quality. The deployment owner must use
the approved real model for the separate Cloud Run delivery phase.

### Initial README questions: choice, rejected option, and reason

| Question | Choice | Rejected option | Reason |
| --- | --- | --- | --- |
| Coverage: what is not covered yet? | Run the complete existing suite and a container smoke check with a synthetic model; report this scope explicitly. | Claim that a passing API fixture check certifies the approved model or Cloud Run deployment. | A fixture demonstrates service behavior, not the real model's accuracy or a live cloud revision. The separately recorded baseline recomputation/tolerance and defect drill remain later team tasks. |
| Machine: what does a clean runner lack? | Obtain dependencies through a locked install and create the clearly labelled smoke fixture on the runner. | Depend on a teammate's `.venv`, ignored model files or local MLflow database. | Only committed files are checked out. Laptop artifacts are not runner-produced evidence. |
| Trigger: which changes start checks? | Check every PR, pushes to the team's integration branch `main`, and manual dispatch; use no path filters. | Check only pushes after a merge or omit tests for documentation changes. | PRs get feedback before integration; the merged revision is checked too, and README/workflow changes can affect reproducibility. |
| Order: what should fail first? | Locked install, style, preflight, all tests, then the dependent Container job. | Build containers before finding basic style or test failures. | Cheap failures stop work early. `needs: checks` prevents the expensive job from starting when Checks fails. |
| Evidence: what can CI claim about the model? | Identify the checked commit, built image ID and smoke model version, and keep runner-produced output. | Cite a laptop training run or the production model's metadata as proof that CI evaluated it. | CI can claim only the installation, tests, build and HTTP checks it performed on its own inputs. |

### Reproduce the Checks job locally

From the repository root, run these PowerShell commands one at a time. Stop at
the first non-zero exit code and diagnose that command before continuing.

```powershell
$env:MLFLOW_DISABLE_TELEMETRY = "true"
$env:DO_NOT_TRACK = "true"
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked python -m bike_demand.preflight
uv run --locked pytest -q --junitxml=ci-results/checks/pytest.xml
```

### Reproduce the Container job without using your local model

After committing the changes, create a disposable checkout. This keeps your
existing `artifacts/` model separate from the synthetic fixture.
Run one command at a time and stop at the first failure. Docker Desktop must
be running. The example publishes the API on loopback port 8004.

```powershell
$lab6ReviewPath = Join-Path $env:TEMP ("alna-ci-" + [guid]::NewGuid().ToString("N"))
git worktree add --detach "$lab6ReviewPath" HEAD
Push-Location "$lab6ReviewPath"
$lab6ReviewSha = (git rev-parse HEAD).Trim()
$lab6ReviewVersion = "ci-smoke-$lab6ReviewSha"
$lab6ReviewImage = "alna-ci-smoke:$lab6ReviewSha"
$env:MLFLOW_DISABLE_TELEMETRY = "true"
$env:DO_NOT_TRACK = "true"
uv sync --locked
uv run --locked python ci/create_smoke_model.py --output-dir artifacts --git-sha $lab6ReviewSha
docker build --build-arg "VCS_REF=$lab6ReviewSha" -t $lab6ReviewImage .
docker image inspect $lab6ReviewImage --format '{{.Id}} {{json .Config.Labels}}'
docker run --rm -e MLFLOW_DISABLE_TELEMETRY=true -e DO_NOT_TRACK=true $lab6ReviewImage uv run --locked pytest -q
docker run -d --name lab6-ci-api -p 127.0.0.1:8004:8000 -e "GIT_SHA=$lab6ReviewSha" -e MODEL_PATH=/app/artifacts/model.joblib -e METADATA_PATH=/app/artifacts/model-metadata.json $lab6ReviewImage
curl.exe --fail --retry 30 --retry-delay 1 --retry-connrefused --retry-all-errors --retry-max-time 60 --max-time 2 http://127.0.0.1:8004/health
uv run --locked python check_deploy.py --base-url http://127.0.0.1:8004 --expected-model-version $lab6ReviewVersion --expected-git-sha $lab6ReviewSha
docker logs lab6-ci-api
```

Save the output before cleanup. `docker rm --force lab6-ci-api` removes this
named test container. `Pop-Location` returns to the original checkout; the
temporary worktree can be removed after its evidence has been retained.

### Logs, identities, and handover

The default Bash shell uses `pipefail`, so piping output through `tee` does not
turn a failed command into a successful step. Only evidence upload and cleanup
use `always()`; the required tests and HTTP checker keep their original exits.
MLflow telemetry is disabled throughout the workflow, as it is in the image.

Each job uploads its `ci-results` text files and reports, including failures,
under a run-specific artifact name with 14-day retention. The Container job
records the checked SHA, image ID/labels, expected fixture version, fixture
metadata, build output, inside-image tests, health response, external checker
output and container logs. Model weights are not uploaded as evidence.

Download text evidence into `evidence/lab6/` before it expires. For example,
`gh run view RUN_ID --log-failed` reads the failed steps and
`gh run view RUN_ID --log` reads the complete run; save their output as text.
A run link alone is not a lasting record. Local runs and GitHub runner runs
must be labelled separately.

The tests owner adds the new regression/recompute tests and registers any new
markers. The reviewer owns the independent defect drill. The release owner
adds the main-only, green-run-gated Cloud Run deployment with keyless login,
live identity verification and rollback evidence. Those results and the `m3`
checkpoint must be documented only after they have actually been obtained.

Workflow references:
[GitHub workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax),
[uv in GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/),
[checkout v6.1.0](https://github.com/actions/checkout/releases/tag/v6.1.0),
[upload-artifact v7.0.2](https://github.com/actions/upload-artifact/releases/tag/v7.0.2).

### CI, Tests & Operations Decisions

Part 1: Pipeline Checks & Coverage Questions

| Question | Choice | Rejected Option | Reason |
| :--- | :--- | :--- | :--- |
| **Coverage**<br>*(What do your checks not cover yet?)* | Run the complete existing test suite and a container smoke check with a synthetic model, reporting this scope explicitly. | Claiming that a passing API fixture check certifies the approved production model or Cloud Run deployment. | A fixture demonstrates service behavior, not the real model's accuracy or a live cloud revision. |
| **Machine**<br>*(What does a clean runner not have?)* | Obtain dependencies through a locked install and create the clearly labeled smoke fixture directly on the runner. | Depending on a teammate's local `.venv`, ignored model files, or local MLflow databases. | Only committed files are checked out; laptop artifacts do not constitute runner-produced evidence. |
| **Trigger**<br>*(Which changes start checks?)* | Check every pull request, pushes to the team's integration branch (`main`), and manual dispatch with no path filters. | Checking only pushes after a merge or omitting tests for documentation changes. | PRs receive feedback before integration, the merged revision is verified, and README/workflow changes can impact reproducibility. |
| **Order**<br>*(Which check should fail first, and why?)* | Locked install, style checks (`ruff`), preflight, all unit/integration tests, and then the dependent Container job. | Building containers before finding basic style or test failures. | Cheap failures stop work early, and `needs: checks` prevents expensive container jobs from starting when code checks fail. |
| **Evidence**<br>*(What can CI claim about the model?)* | Identify the checked commit, built image ID, and smoke model version, retaining runner-produced output. | Citing a laptop training run or production metadata as proof that CI evaluated it. | CI can only claim the installation, tests, builds, and HTTP checks it performed independently on its own inputs. |

Part 2: Tests, Defects & Tolerance Questions

| Question | Choice | Rejected Option | Reason |
| :--- | :--- | :--- | :--- |
| **Defects**<br>*(Which bug does each test catch?)* | The regression test (`test_prediction_matches_saved_model` tagged with `@pytest.mark.regression`) catches unintended numeric drift, feature mismatch bugs, or code regressions that alter prediction outputs away from established baseline expectations. | Relying solely on basic syntax linting to catch runtime prediction errors. | Syntax checks do not verify numerical stability or output correctness over time. |
| **Failing / Records**<br>*(Can you make each test fail?)* | Yes, modifying the expected baseline output or altering input feature behavior forces an immediate failure, satisfying the red-to-green defect verification rule. | Passing tests by loosening assertions when code outputs change unexpectedly. | Muting or loosening assertions hides regressions instead of catching real defects. |
| **Tolerance**<br>*(Where does your number come from?)* | Tolerances (`pytest.approx` or defined error bounds) are derived from measured floating-point variation and deterministic model test fixture outputs. | Using arbitrary large tolerances or ignoring precision boundaries. | Strict tolerances ensure that numeric regressions or unstable feature transformations are detected immediately. |
| **Repair**<br>*(Did you fix the cause or hide it?)* | Failures are resolved by fixing the underlying code logic or restoring expected model parity rather than suppressing test execution or modifying lockfiles. | Deleting failing tests or regenerating lock files to bypass failures. | Preserves absolute pipeline integrity and ensures code readability and reliability over a 3-month horizon. |
| **Repair**<br>*(Did you fix the cause or hide it?)* | Failures are resolved by fixing the underlying code logic or restoring expected model parity rather than suppressing test execution or modifying lockfiles. | Deleting failing tests or regenerating lock files to bypass failures. | Preserves absolute pipeline integrity and ensures code readability and reliability over a 3-month horizon. |

## Pipeline and gate

Lab 7 starts with a **training-only component**. It does not yet implement the
end-to-end decided-candidate command, evaluator, gate or promotion workflow.
Shared interfaces and handoffs are documented in
[the Lab 7 contract](docs/lab7-contract.md).

### Clean-checkout commands

Use Python 3.12 and the existing lock file from the repository root:

```powershell
uv sync --locked
uv run --locked python -m bike_demand.pipeline check --config configs/baseline.yaml
```

The check validates the frozen CSV, twelve ordered predictors and chronological
partition counts (8,645 train / 4,358 validation / 4,376 held test). It produces
no model or evaluation score. After committing training code and configuration:

```powershell
uv run --locked python -m bike_demand.pipeline train --config configs/baseline.yaml
```

This command fits only the 2011 training rows and prints the new candidate
location under `artifacts/candidates/candidate-<uuid>/`. Each bundle contains the
model, metadata, exact config and lock, data manifest, actual environment,
partition identities and a final `bundle.json` with SHA-256 and size per file.
An optional `--candidate-id candidate-<name>` is write-once. Incomplete attempts
have no completion marker and cannot be reused. Local files can still be edited;
consumers must verify hashes and the version-store owner must make them durable.

Training requires committed tracked files and training inputs. Unrelated
untracked notes are allowed. No accepted pointer, default API model, existing
MLflow database or legacy metrics file is changed. Exit 0 means **trained**, with
`evaluation_status: not_evaluated`; it is not eligibility or deployment approval.
The original `bike_demand.train` remains for baseline compatibility and must not
be used as the Lab 7 candidate entry point because it overwrites fixed artifacts.

### Verify a saved candidate before loading

The review identified missing consumer-side checks for a saved bundle. The
shared reader in `bike_demand.bundles` now verifies the manifest schema, exact
file names, byte counts, SHA-256 values and metadata cross-references before
model loading. `load_verified_model` loads the checked bytes from memory.
The evaluator owner must use this reader in the forthcoming consumer.

To audit the local candidate selected in PowerShell:

```powershell
uv run --locked python -m bike_demand.pipeline verify --candidate-dir $lab7Candidate.FullName
```

Use `--expected-bundle-sha256` to bind verification to a manifest digest recorded
independently in trusted evidence or immutable storage. Success reports
`bundle_verified` and `not_evaluated`; it does not establish policy eligibility.
An invalid selected bundle exits 1 with a reason and remains unchanged.
Pytest checks corrupted synthetic bundles, including the reviewer's changed
manifest-digest case. It does not automatically inspect ignored local artifacts.

### Pipeline design decisions

| Question | Choice | Alternative | Reason |
| --- | --- | --- | --- |
| Stages | Separate input check, candidate training, evaluation, gate and manual promotion; the first two are implemented here | One training function overwriting the served model | Each stage has a distinct result and write boundary |
| Entry point | One module with `check` and `train`; lead adds the full decided-candidate stage after Members 2–3 integrate | A sequence of undocumented notebook cells | Explicit CLI inputs support a clean checkout and later composition |
| Failure | Nonzero exit and reason; no success marker for incomplete training; no automatic numeric retries | Retry a failed policy result until it passes | Failures stay visible and cannot change the accepted model |
| Partial state | Reserve a unique directory; publish `bundle.json` last; refuse an existing ID | Reuse partly written output as a complete candidate | Consumers can distinguish complete bytes from interrupted work |
| Identity | Version, model/bundle hashes, data/config/lock, full Git revision, installed environment and observation identities | Filename or seed alone | A decision must refer to the exact evaluated bytes and context |

The training component bounds RF runs to 1–200 trees, depth 1–20, one worker and
an explicit seed. These proposed compute bounds need team review. Member 3 must
commit policy, rationale and candidate budget before real candidate evaluation;
no quality threshold is inferred from observed results in this PR.

Member 2 supplies a trusted frozen incumbent and evaluates all three predictors
(candidate, incumbent, train-mean baseline) on the same validation rows. Member 3
produces reasoned `eligible`, `rejected` or `blocked` decisions with mandatory
quality, operation and integrity checks. Missing reference or invalid evidence
blocks a decision from becoming eligible. All outcomes leave accepted/served
state unchanged until Member 4's separately reviewed manual promotion.

### Cloud Run transition

The previous CI deployment job generated a **synthetic smoke fixture** and
deployed automatically on pushes to `main`. Its final step echoed success; it
did not perform the live identity check previously described here. This Lab 7
change removes that deployment job and retains `Checks` and `Container`.
It does not contact or replace the current live service.

Member 4 must supply manual promotion from reviewed green `main`, deployment of
the exact eligible bundle, keyless authentication, live `/health` and `/predict`
identity verification, and retained previous/current accepted bundles and Cloud
Run revisions for Lab 8. These results remain pending; neither the old success
message nor tag `m3` proves them. Tag `m4` follows completion of Labs 7–8.

See the [Week 4 team report](reports/week-04-team.md) and
[Member 1 local evidence](evidence/lab7/member1/README.md).

## Pipeline and Gate
- **Quality Gate Policy:** Evaluates candidate models against mandatory quality, operational, and integrity criteria.
- **Outcomes Supported:** `Eligible`, `Rejected`, and `Blocked/Error`.
- **Decision Records:** Generated decision records are stored in `evidence/decision_record.json` detailing policy version, identities, measurements, and outcome reasons.
- **Testing:** Unit tests verifying valid eligibility, rejections, missing provenance, and non-finite metric blocking are implemented under `tests/test_gate.py`.

### Promotion
The candidate model is promoted manually from reviewed `main`:
    uv run python -m bike_demand.promote
This moves the current `models/accepted/` bundle to `models/previous/` and copies the candidate artifacts into `models/accepted/`.

### Rollback (without retraining)
To recover the previous accepted model:
    Copy-Item models/previous/* models/accepted/ -Force
Then rebuild the Docker image.

## 1. Member 1 (Lead — Infrastructure, Baseline & Runbook Lead)
- **Live Service Verification:** Validated health and prediction endpoint contracts.
- **Baseline Measurement:** Recorded pre-incident reference traffic, UTC time window, p95 latency, and error metrics on Cloud Run.
- **Runbook Framework:** Published initial [RUNBOOK.md](RUNBOOK.md) at repo root for operational guidance.
