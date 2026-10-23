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
