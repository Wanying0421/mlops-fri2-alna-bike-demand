# Lab 7 shared contract — Member 1 proposal

This contract is supplied with the training component for peer review. Numeric
quality thresholds and operational limits belong to Member 3's reviewed policy;
none have been selected from a candidate's observed scores here.

## Owners and integration order

| Member | Ownership | Dependency / handoff |
| --- | --- | --- |
| 1 — Lead | Input validation, training, candidate provenance, final orchestration and documentation | Provides this bundle format; integrates the evaluator and gate after their PRs pass |
| 2 — Reviewer | Freeze the accepted reference, evaluate three predictors, independently challenge the decision | Needs the actual trusted accepted bundle and Member 3's committed policy before course-candidate evaluation |
| 3 | Gate policy, decision records and failure tests | Commit policy and its justification before evaluating a real candidate; implement quality, operation and integrity checks |
| 4 | Durable version store, manual promotion and Cloud Run verification | Requires an eligible decision, independent review and reviewed green `main`; retain the previous bundle and cloud revision |

Members 2–4 can prepare their components in parallel. Every member owns a PR and
reviews another member's work. A passing training command is not a gate decision.

## Fixed inputs and training budget

- CSV: `data/raw/hour.csv`, checked against `data/manifest.json` without repair.
- Predictors, in order: `season`, `yr`, `mnth`, `hr`, `holiday`, `weekday`,
  `workingday`, `weathersit`, `temp`, `atemp`, `hum`, `windspeed`.
- Train: 2011, 8,645 rows. Validation: January–June 2012, 4,358 rows.
  Held test: July–December 2012, 4,376 rows. No held-test metric is produced.
- Configuration keys remain `data`, `features`, `model`. Only RF settings vary.
  The component accepts 1–200 trees, depth 1–20, one worker and an explicit
  integer seed from 0 to 2^32−1. These are proposed compute bounds, not a quality
  threshold or evidence of an approved experiment.
- Initial configuration is the existing 50-tree, depth-10, seed-42 preset.
  Do not launch a parameter search or select settings after inspecting scores.
  The team must review and commit its candidate budget and gate policy first.
- Training requires a committed HEAD and no tracked changes or untracked
  training inputs. Unrelated untracked notes do not prevent training.

## Member 1 commands available now

From the repository root after `uv sync --locked`:

```powershell
# Read-only validation: no training, evaluation or promotion.
uv run --locked python -m bike_demand.pipeline check --config configs/baseline.yaml

# Training component only. Commit code/config first; do not treat exit 0 as approval.
uv run --locked python -m bike_demand.pipeline train --config configs/baseline.yaml
```

An optional `--candidate-id candidate-<name>` reserves a write-once ID. Otherwise
the command creates `candidate-<uuid>`. An existing ID, including an incomplete
attempt, is refused. A new ID starts a new attempt; it does not make a failed
quality result pass.

The old `bike_demand.train` entry point is retained for the existing baseline
tests. It writes fixed legacy artifacts and performs validation scoring: **do not
use it as the Lab 7 candidate entry point**.

## Candidate format: schema version 1

Each complete local candidate is under `artifacts/candidates/<candidate-id>/`:

| File | Contract |
| --- | --- |
| `model.joblib` | RF fitted on train rows only; no validation or held-test prediction in Member 1's code |
| `model-metadata.json` | `model_version`, `training_commit`, `tracked_tree_clean`, timestamp, ordered `features`, data/config/lock/model SHA-256, effective model parameters, seed, training row count, `evaluation_status: not_evaluated` |
| `config.yaml` | Exact configuration bytes used for this run |
| `uv.lock` | Exact dependency lock bytes; do not regenerate for a run |
| `data-manifest.json` | Frozen data identity, copied without modifying the CSV |
| `environment.json` | Actual Python, platform and installed package versions |
| `partitions.json` | Row counts, date ranges and SHA-256 of each ordered list of `instant` IDs; the dataset digest also binds the labels |
| `bundle.json` | Completion marker, `schema_version: 1`, `candidate_id`, `stage: trained`, `evaluation_status: not_evaluated`, and `files` mapping each other filename to its `sha256` and `bytes` |

The model metadata uses the API's existing `model_version` and `features` names.
The service's `GIT_SHA` environment value is a separate deployment responsibility;
putting a SHA in metadata does not automatically configure the running service.

`bundle.json` is written last using a temporary file and rename. Consumers must
reject a missing marker, unknown schema, wrong identity, missing files, unsafe
filenames or digest/size mismatch **before loading any trusted joblib file**.
The digest of `bundle.json` itself must be recorded by evaluation and decision
records. A digest proves identity, not trust in arbitrary downloaded pickle data.

Do not add evaluation files to an already complete training bundle. The command
never reuses an ID, but ordinary local files remain writable: Members 2–4 must
recheck hashes, and Member 4 must provide durable immutable version storage.
Ignored laptop artifacts and local MLflow databases are not durable evidence.

## Evaluation and decision interfaces to implement

Suggested public Python functions, to agree in the respective PRs:

```python
# Member 2: bike_demand.evaluate
evaluate_candidate(root, candidate_dir, reference_dir, policy_path) -> dict

# Member 3: bike_demand.gate
decide_candidate(root, candidate_dir, reference_dir, policy_path, evaluation) -> dict
```

Use `pathlib.Path` arguments and JSON-compatible results. The lead will add a
single end-to-end CLI stage calling these components after their contracts and
implementations are reviewed. It must stop on a missing component/input and
produce a reasoned blocked record rather than claim eligibility. That CLI stage
is **not implemented by this training-only PR**; the lab's decided-candidate
one-command requirement remains an integration task.

Reserve these paths, adjusting the backend together if needed:

- `configs/gate-policy.json`: Member 3's committed policy with justification and
  budget. Record both its digest and the commit containing the policy.
- `artifacts/accepted/<version>/`: locally materialized trusted reference
  bundle from Member 4's durable store; never synthesize an accepted reference.
- `artifacts/accepted.json`: accepted pointer managed only by Member 4.
- `evidence/lab7/evaluations/<evaluation-id>.json`: Member 2's portable evidence,
  outside the training bundle. Compare candidate, accepted reference and mean
  trained on 2011 labels on the same ordered validation observations and labels.
- `evidence/lab7/decisions/<decision-id>.json`: Member 3's reasoned decision,
  outside the training bundle. A retry creates a new record; do not edit history.

At minimum, bind both records to candidate version/model/bundle digest, accepted
version/model/bundle digest, data and configuration identity, code/environment,
policy digest/commit, validation observation identity/count, metric definition,
all measured values, operational measurement context and evidence references.
The decision must list each quality, operation and integrity check with its
observed/required value and reason. Missing or invalid evidence must never be
interpreted as passing. Missing reference artifacts block comparison.

| Gate outcome | Meaning | Accepted / served state |
| --- | --- | --- |
| `eligible` | All three required claims pass on valid complete evidence | Unchanged until separate reviewed manual promotion |
| `rejected` | Valid, complete evidence violates the committed policy | Unchanged |
| `blocked` | A required input/check is missing, invalid, incompatible or cannot run | Unchanged |

Member 2 must challenge a real claim independently. Capture before/after
accepted pointer, bundle hashes and served identities; a log-only test does
not prove that rejection preserved the service.

## Promotion boundary and remaining work

The previous CI `deploy` job created a synthetic smoke model and deployed on
every push to `main`; its final verification step only printed a success message.
This PR removes that job while retaining `Checks` and `Container`. It makes no
call to the existing Cloud Run service. Historical Lab 6 deployment claims need
actual cloud evidence; tag `m3` alone cannot establish model or service identity.

Member 4 must implement manual promotion of the **exact eligible bytes** from
reviewed green `main`, keyless cloud authentication, live `/health` and `/predict`
identity checks, and retained previous/current bundles plus Cloud Run revisions
for Lab 8. Recheck the incumbent before committing a switch; document failure
recovery if the store and service cannot be changed atomically. A partial local
candidate is never a release. Do not create tag `m4` until Labs 7–8 are complete.
