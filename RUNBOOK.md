# Operational Runbook - Bike Demand Service

## 1. Recognizable Symptoms & Scope
- **Latency Spike:** p95 request duration exceeds 500ms.
- **Error Rate Increase:** Non-200 HTTP responses on /predict or /health returning HTTP 503.
- **Scope:** Affects Cloud Run traffic routed to the current active revision.

## 2. First Checks
1. Check Cloud Run service health (GET /health -> 200/503).
2. Inspect recent Cloud Run logs for exceptions or model loading errors.
3. Verify active revision identity and model checksum against the retained accepted release record.

## 3. Safe Rollback Targets & Procedure
- **Target:** Exact retained compatible Cloud Run revision and verified model bundle.
- **Execution:** gcloud run services update-traffic bike-demand --to-revisions=REVISION_NAME=100 --region=REGION

## 4. Fresh Verification Steps
1. Exercise health endpoint (GET /health -> 200 OK).
2. Send test probe requests to POST /predict.
3. Monitor error rates and p95 latency.

## 5. Escalation & Last Verified Context
- **Last Verified Context:** Lab 8 Incident Response Drill.
- **Escalator / Owner:** Team Lead (Member 1).
