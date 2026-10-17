# Week 2, Labs 3–4: dependency lock, Docker, clean rerun, tested prediction API

## Team and roles

Repository: mlops-fri2-alna-bike-demand

Members: Laroche22, BoutalebAnas, nouhasantir, Wanying0421

Lead Lab 03: Laroche22 (Member 1 - Dockerfile & .dockerignore)

Reviewer Lab 03: Wanying0421 (Member 4 - Reviewer: Reproduction & comparison)

Dependency Locking (Member 2): BoutalebAnas

README and Team Report (Member 3): nouhasantir

## Repository and pull requests

PR #5: Lab 3: containerize the Lab 2 baseline by Laroche22, merged to integration branch (Lead/Dockerfile integration).   
PR #6: Add dependency lock evidence for Lab 03 by BoutalebAnas, merged to integration branch (Dependency locking & validation).   
Merge commits: Verified and integrated into the main/develop branch workflow.

## Setup, preflight and quality checks (commands and actual results)

docker build -t mlops-baseline:lab3 . : Container image successfully built with pinned Python 3.12-slim and uv binary.
docker run --rm mlops-baseline:lab3 : Baseline pipeline executed successfully inside the isolated container environment.   
uv sync --locked : Dependencies installed successfully matching the committed lockfile.
uv lock --check : Verified manifest and lockfile consistency.

## Core outcomes: Locked, Packaged, Rerun

Locked: Dependencies are strictly driven by the committed uv.lock. Removing or modifying the lock file triggers a visible failure during uv sync --locked rather than silent regeneration.   
Packaged: Custom Dockerfile and .dockerignore created to isolate the build context, stripping out host virtual environments (.venv), git metadata, caches, and secrets.   
Rerun: Fresh container successfully reproduced the Lab 2 baseline from unchanged inputs without relying on host state or bind-mounted source directories.  

## Dockerfile choices, .dockerignore and lock verification

Base Image: Pinned python:3.12-slim combined with the official Astral uv binary (--from=ghcr.io/astral-sh/uv) to guarantee deterministic environment setup.   
Layer Optimization: Copied pyproject.toml and uv.lock prior to source code (src/) so that code edits do not invalidate the heavy dependency installation layer.   
Context Isolation (.dockerignore): Excluded .venv, .git, __pycache__, .pytest_cache, artifacts, and .env files.   
Lock Failure Demonstration:
       Removing the lock file (rm uv.lock && uv sync --locked) yielded: error: Unable to find lockfile at 'uv.lock', but '--locked' was provided.   
       Stale lock file update test yielded: error: The lockfile at 'uv.lock' needs to be updated, but '--locked' was provided.

## Execution evidence, image ID, and baseline comparison

Docker Image ID: f7907cb168e5   
Model Version / Run ID: Model Version baseline-6a448105fa7, Run ID b75fb82262984b3885b1f4c430e2a214   
Observed Validation MAEs:
       Naive Train Mean MAE: 154.23   
       Random Forest MAE: 86.85   
Readback & Verification Metrics:
       reload_mae: 86.84685685591091   
       reload_mae_delta: 0.0   
       metadata_matches: true   
       logged_model_bytes_match: true   
       prediction_max_abs_delta: 0.0
## Review observation and author's response
Review : Rebuilt the project strictly following the README.md instructions from a clean checkout and verified container isolation.

Author's response: Confirmed clean container build (mlops-baseline:lab3), successful baseline execution, and accurate output retrieval commands. Approved and merged.

## Contribution and assistance/recovery acknowledgement

Laroche22: Authored the Dockerfile and .dockerignore, managed container builds, and coordinated integration (Lead).   
BoutalebAnas: Implemented dependency locking verification, tested missing/stale lock behavior via uv sync --locked, and gathered execution logs (Member 2).   
nouhasantir: Authored build, test, lock-check, and artifact retrieval instructions in README.md and compiled this team report (Member 3).
Wanying0421: Performed independent clean-checkout reproduction and peer review (Reviewer).   
References: Official Astral uv Docker guide and Docker build best practices.

## Blockers and next action
Blockers: Local path environment warnings with pre-existing virtualenvs resolved successfully by adhering strictly to containerized execution paths. No remaining blockers.

Next action: Transition directly to Week 2, Lab 4 (Prediction API implementation, Pydantic input validation, FastAPI endpoints, and containerized test suite).

## Screenshots (saved in reports/images/)
lab3-validation-mae-output.png — Baseline execution metrics showing validation MAEs and readback verification.  

<img width="568" height="374" alt="lab3-validation-mae-output" src="https://github.com/user-attachments/assets/b679a49b-1c91-433f-b455-70a91118a0eb" />


lab3-review-lock-error.png — Terminal evidence proving that removing uv.lock causes uv sync --locked to fail visibly.  

<img width="821" height="74" alt="lab3-review-lock-error" src="https://github.com/user-attachments/assets/06255fe7-82f8-4b3f-880e-00e7e262c2e3" />

lab3-review-image-id.png — Docker Desktop interface showing image mlops-baseline:lab3 with ID f7907cb168e5.

<img width="738" height="236" alt="lab3-review-image-id" src="https://github.com/user-attachments/assets/1c1c00c2-1f74-4f0b-b1c9-50b5851bdae7" />

lab3-baseline-execution.png — Container run output showing partition counts, feature schema, and configuration settings

<img width="641" height="677" alt="lab3-baseline-execution" src="https://github.com/user-attachments/assets/6c0e4516-44ca-47df-a494-4472c0371cf0" />
