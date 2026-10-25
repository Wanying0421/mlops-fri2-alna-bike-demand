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

# Lab 6: Team Deployment & Operational Report

- **Team Name**: `alna`
- **Repository**: `mlops-fri2-alna-bike-demand`
- **Deployment Platform**: Google Cloud Run (`europe-west1`)
- **Service Name**: `mlops-fri2-alna-bike-demand`

---

## 1. Executive Summary & Pipeline Flow
Our team established a 3-stage automated CI/CD pipeline using GitHub Actions to continuously validate and deliver the bike demand prediction service to Google Cloud Run.

The execution sequence is structured as follows:
1. **Checks Job**: Runs code formatting (Ruff), static checks, preflight verification, and the complete pytest suite under `tests/`.
2. **Container Job**: Generates a synthetic model fixture, builds the Docker container, executes tests inside the container, and verifies local HTTP endpoints.
3. **Deploy Job**: Triggers exclusively on `push` events to `main` to deploy the verified container image to Cloud Run using Workload Identity Federation (WIF).

---

## 2. Core Operational Guarantees (Gate, Identity, Proof, Undo)

### Gate (Deployment Conditions)
- **Constraint**: The `deploy` job relies on `needs: container` and a branch condition (`if: github.ref == 'refs/heads/main' && github.event_name == 'push'`).
- **Guarantee**: Broken code or unmerged Pull Requests cannot reach production. All checks must turn green before deployment is possible.

### Identity (Keyless Authentication)
- **Mechanism**: Authenticates to GCP via Workload Identity Federation (WIF) using `google-github-actions/auth@v2` with `id-token: write`.
- **Security**: No long-lived service account JSON keys are stored in repository secrets. Authentication relies entirely on short-lived OIDC tokens.

### Proof (Live Verification)
- **Verification**: Following Cloud Run deployment, an automated HTTP check (`check_deploy.py`) queries the live service endpoint.
- **Assertion**: Ensures the live service's reported `git_sha` and `model_version` match the exact Git commit that triggered the build.

### Undo (Rollback & Incident Recovery)
- **Traffic Rollback**: Traffic can be instantly shifted to a previous revision via the GCP Console or `gcloud run services update-traffic`.
- **Git Revert**: Merging a `git revert` on `main` triggers a fresh, reproducible build and redeployment of the prior stable state.

---

## 3. Evidence & Artifact Management
- **Artifact Retention**: Test logs, JUnit reports, and container build outputs are uploaded as GitHub Actions artifacts with a 14-day retention window.
- **Isolation**: Clean runners build dependencies strictly from `uv.lock`. Local environment artifacts (`.venv`, local models) are excluded to guarantee clean-room reproducibility.

---

## 4. Team Member Contribution Matrix

| Member | Focus Area & Key Deliverables |
| :--- | :--- |
| **Member 1** | Pipeline structure, Ruff linting/formatting rules, and unit/contract test suites. |
| **Member 2** | Containerization, Dockerfile optimizations, and in-container test execution. |
| **Member 3** | Cloud Run service configuration, region setup (`europe-west1`), and GCP IAM roles. |
| **Member 4** | Cloud Run automated deployment job, Workload Identity Federation (WIF) integration, and deployment verification. |
