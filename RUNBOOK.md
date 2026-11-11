# Operational Runbook - Bike Demand Service

## 0. Service Identity
- *Project:* mlops-ece-group4-and-group1
- *Service:* mlops-fri2-alna-bike-demand
- *Region:* europe-west1
- *URL:* https://mlops-fri2-alna-bike-demand-709271018248.europe-west1.run.app
- *Access:* The service does not allow anonymous calls (browser returns 403). Calls need an identity token and the Cloud Run Invoker role.
  bash
  curl -i -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
    https://mlops-fri2-alna-bike-demand-709271018248.europe-west1.run.app/health
  
- *Known revisions (as of 2026-11-08):*
  - mlops-fri2-alna-bike-demand-00006-t77: 100% traffic (recovered, MODEL_PATH /app/artifacts/model.joblib)
  - mlops-fri2-alna-bike-demand-00005-h66: 0% traffic (do not use: MODEL_PATH /app/artifacts/not-there.joblib, returns 503)
  - mlops-fri2-alna-bike-demand-00004-v4l: 0% traffic (do not use: MODEL_PATH /app/models/does_not_exist.joblib, returned 503 after the rollback)


## 1. Recognizable Symptoms & Scope
- *Latency spike:* p95 request duration is clearly above the Cloud Run baseline (see section 6a: about 61 ms on /health). The old 500 ms threshold is only a rough alert level.
- *Error rate increase:* non-200 responses on /health, or 5xx on /predict. /health returns 503 when no usable model is loaded.
- *Note:* Invalid input must still return 4xx. This is expected validation behavior, not an incident.
- *Scope:* Affects Cloud Run traffic routed to the current active revision.

## 2. First Checks (cheapest first)
1. Call GET /health with an identity token. Record the status code and the UTC time.
2. Open Cloud Run > Logs. Look for exceptions, model loading errors, or missing file errors. Note the first error time (UTC).
3. Open Cloud Run > Revision History. Which revision has traffic? When was it created? Did a new revision appear before the symptom started?
4. Open the active revision > Containers. Compare its image and environment variables with the other revision.
5. Check the model_version in a /predict response against the retained accepted record.
6. Write down which boundaries you checked and which you did not (service/revision, model, configuration, inputs).

## 3. Safe Rollback Targets & Procedure
- *Target:* Retained Cloud Run revision mlops-fri2-alna-bike-demand-00006-t77 (100% traffic after recovery on 2026-11-08).
*Model version of target:* ci-smoke-7d7e10fd3a3f36533c077732d21d07177fad32d6. Note: this is the CI smoke fixture (constant prediction), not the accepted model baseline-dd901b9c0fa5, which is not yet deployed. Update this line after the accepted model is deployed.
- *Do not use:* 00001-hmb unless the team confirms it is compatible. An older revision is not automatically a safe target.
- *Before switching:* Confirm the target's model version, checksum, feature schema and configuration match the accepted record. If a checksum does not match, do not load or relabel the artifact.
- *Execution (gcloud):*
  bash
  gcloud run services update-traffic mlops-fri2-alna-bike-demand \
    --to-revisions=mlops-fri2-alna-bike-demand-00006-t77=100
    --region=europe-west1
  
- *Execution (web console):* Cloud Run > mlops-fri2-alna-bike-demand > Revision History > Manage traffic > select 00002-j9t = 100% > Save.
- *Note:* Do not delete any revision. Do not retrain as the recovery action.

## 4. Fresh Verification Steps
After the rollback, collect new evidence (not just a successful command):
1. *Identity:* Confirm the active revision is 00002-j9t with 100% traffic. Compare image and variables with the retained expectation.
2. *Behavior:* Send fresh requests to the live URL with an identity token:
   - GET /health returns 200.
   - POST /predict with a valid body returns a finite, nonnegative prediction and the expected model_version.
   - An invalid body still returns 4xx.
3. *Signals:* Check Cloud Run logs and metrics after the rollback time. Record the observation window, request count, error count and p95.
4. *Optional check script:*
   bash
   uv run python check_deploy.py \
     --base-url https://mlops-fri2-alna-bike-demand-709271018248.europe-west1.run.app \
     --expected-model-version ci-smoke-7d7e10fd3a3f36533c077732d21d07177fad32d6 \
     --expected-git-sha <set after redeploy with GIT_SHA>

   (The current revision reports git_sha "unknown" because GIT_SHA was not set at deploy time. Set GIT_SHA on the next deployment so this check can verify it.)

5. Compare baseline, incident and recovery using the same definitions (section 6a).

## 5. Escalation, Limitations & Last Verified Context
- *Escalation / Owner:* Member 1 (Lead). If rollback fails or the target is unclear, stop and escalate. Record the exact error message.
- *Limitations:*
  - The baseline covers /health only, not /predict.
  - 50 sequential requests over about 18 seconds is a small, short sample.
  - Service health is not the same as prediction quality.
  - This runbook has not yet been tested by another operator.
  - *Last verified context:* Lab 8 drill, 2026-11-08 by @NouhaSantir.

## 6. Baseline Reference Windows

### 6a. Cloud Run baseline (primary)
- *Measured by:* Member 1, in Google Cloud Shell
- *Service:* mlops-fri2-alna-bike-demand (europe-west1)
- *Endpoint:* GET /health (with identity token)
- *Window (UTC):* 2026-11-07T21:29:29Z to 2026-11-07T21:29:47Z (about 18 seconds)
- *Total requests:* 50, sent one after another
- *Non-200 responses:* 0 (error rate 0%)
- *p95 latency:* 0.060835 s (about 61 ms)

### 6b. Local reference (not comparable with Cloud Run)
- *UTC window:* 2026-03-30 10:00:00 - 10:15:00
- *Requests:* 1,000 sent at 10 req/s (local test)
- *p95 latency:* 245 ms
- *Failed valid requests:* 0
- *Note:* Measured locally, not on Cloud Run. Do not compare directly with 6a.