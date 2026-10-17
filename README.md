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

## Lab 3: Containerized Baseline and Dependency Locking

### Prerequisites
* Docker installed and running on your machine.
* Git for checking out the exact revision.

### 1. Building the Docker Image
To build the container image from a clean checkout, run the following command from the root of the repository:

```bash
docker build -t mlops-baseline:lab3 .
```
#### 2. Running the Baseline and Tests
## Run the Baseline Pipeline
To execute the core ML baseline pipeline inside a fresh, isolated container:

```Bash
docker run --rm mlops-baseline:lab3
```
## Run the Test Suite
To verify that all unit and integration tests pass successfully inside the container environment:

```Bash
docker run --rm mlops-baseline:lab3 uv run --locked pytest -q
```
### 3. Verifying Dependency Locking
## To test that a stale or missing lockfile correctly halts execution rather than auto-regenerating:

```Bash
docker run --rm --entrypoint sh mlops-baseline:lab3 -c "rm uv.lock && uv sync --locked"
```
### 4. Retrieving Outputs
## To copy generated artifacts, logs, or model outputs from a container instance:

```Bash
docker run --name temp-container mlops-baseline:lab3
docker cp temp-container:/app/artifacts ./out
docker rm temp-container
```
