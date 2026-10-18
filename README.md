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
docker run --rm -p 8000:8000 -v $(pwd)/artifacts:/app/artifacts -e MODEL_PATH=/app/artifacts/model.joblib -e MODEL_METADATA_PATH=/app/artifacts/model-metadata.json mlops-baseline:lab3
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
docker run --rm --entrypoint uv mlops-baseline:lab3 run python src/bike_demand/baseline.py
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
docker run --name temp-container mlops-baseline:lab3
docker cp temp-container:/app/artifacts ./out
docker rm temp-container
```
