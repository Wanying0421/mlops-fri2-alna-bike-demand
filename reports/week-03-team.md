## Lab 5: Service Deployment, Structured Logs & Model-Version Checks

### 1. Student / Team & Links
- **Team Integration Branch:** `main` (via feature pull requests)
- **Team Members & Responsibilities:**
  - **Member 1 (anasboutaleb):** Containerization (Docker), environment configuration (`PORT`), and Cloud Run deployment with live endpoint verification.
  - **Member 2 (wanying0421):** Structured JSON logging middleware in FastAPI (`src/bike_demand/api.py`) capturing single-line events (`event`, `status`, `duration`, `model_version`).
  - **Member 3 (laroche22):** Outside check validation script (`check_deploy.py`) verifying model versions and Git SHAs over the network with strict exit codes (`1` on mismatch).
  - **Member 4 (nouhasantir):** PR code reviews, "Deploy" documentation in `README.md` (answering the 10 operational FAQ questions), and team reporting.

### 2. Test and Execution Results
- **Docker Build & Local Runtime:**
  ```bash
  docker build -t bike-demand-svc:lab5 .
  docker run --rm -d --name lab5-container -p 127.0.0.1:8000:8000 bike-demand-svc:lab5
  ``

**Observed Outputs & Verification:**

GET /health successfully returned HTTP 200 OK with the expected health status and loaded model version.

POST /predict successfully processed inference inputs, returning valid bike demand predictions and matching model version metadata.

Error modes were verified: invalid input shapes correctly triggered 422 Unprocessable Entity, and missing model files triggered explicit 503 Service Unavailable responses.

### 3. Screenshots & Evidence Links
Figure 1 (reports/images/lab-05-local-docker.png): Local Docker container startup logs, Uvicorn execution state, and successful curl / Python requests validation outputs confirming endpoint stability.

Figure 2 (reports/images/dockerfile-config.png): Build context configuration ensuring tracking directories, reports, and model artifacts are properly bundled into the image.

### 4. Decisions and Rationale
Environment-Driven Configuration: Configured port and path variables dynamically via environment variables rather than hardcoding values to guarantee identical execution behavior across local laptops, CI pipelines, and cloud runtimes.

Fast-Fail Architecture: Enforced explicit 503 service status returns during model loading failures rather than fallback defaults, ensuring immediate detection by automated monitoring and outside check scripts.

### 5.Blockers / Missing Evidence
Status: All blockers resolved. Container builds, local endpoint tests, and automated integration checks successfully passed without errors.

