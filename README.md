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
## lab 4: API container

A containerized MLOps project for predicting bike-sharing demand using Python, `uv`, FastAPI, and Docker.


### Project Structure

- `src/bike_demand/`: Core package containing the pipeline scripts (training, data preflight, validation) and the prediction API.
- `configs/`: Configuration YAML files for training and model baselines.
- `tests/`: Automated unit and integration tests.
- `Dockerfile`: Optimized container setup for running the service.

### Prerequisites & Installation


1. **Clone the repository:**
   ```bash
   git clone [https://github.com/Wanying0421/mlops-fri2-alna-bike-demand.git]
   cd mlops-fri2-alna-bike-demand
   ```
Install dependencies:

```Bash
uv sync --locked
```
### Running Locally
1. Model Training
To run the baseline training pipeline locally:

```Bash
uv run python -m bike_demand.train --config configs/baseline.yaml
```
2. Running Tests
To execute the test suite using pytest:

```Bash
uv run pytest -q
```

### Docker Containerization
The application is fully containerized using Docker, leveraging uv for a reproducible and clean environment.

1. Build the Docker Image
From the root directory of the project, run:

```Bash
docker build -t bike-demand:lab4 .
```
2. Run the Container
Start the container and expose port 8000:

```Bash
docker run --rm -p 127.0.0.1:8000:8000 bike-demand:lab4
```
### API Endpoints & Usage
Once the container or local server is running, you can interact with the API:

Health Check:

```Bash
curl localhost:8000/health
```
Make a Prediction (POST /predict):

```Bash
curl -X POST localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"season": 1, "mnth": 1, "holiday": 0, "yr": 0, "hr": 10, "weekday": 1, "workingday": 1
```
Using PowerShell:

```PowerShell
Invoke-RestMethod -Uri "http://localhost:8000/predict" -Method Post -Body '{"season": 1,"mnth": 1, "holiday": 0, "yr": 0, "hr": 10, "weekday": 1, "workingday": 1, "weathersit": 1, "temp": 0.24, "atemp": 0.2879, "hum": 0.81, "windspeed": 0.0}' -ContentType "application/json"
```
### Containerized Testing
To execute the test suite inside the built Docker container:

```Bash
docker run --rm bike-demand:lab4 uv run --locked pytest -q
```
