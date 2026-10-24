# Lab 6 — Member 1 workflow audit

## Source inspected

The supplied Git archive identifies source commit
`6a8088b0b793b3923ed78b8814e57a6be73d7572`.
This document describes the proposed Phase 1 change, not a passing GitHub run.

## Original workflow, read in order

| Lines | Existing behavior | Finding |
| --- | --- | --- |
| 1 | Name `Week 1 checks` | The name describes the old scope. |
| 3–9 | Push/PR filters for `main`; manual dispatch | PRs targeting another branch are not checked. |
| 11–12 | `contents: read` | Preserve least privilege. |
| 14–18 | One Ubuntu 24.04 job; 15-minute timeout | Preserve a bounded Linux runner. |
| 19–21 | `checkout@v6`; persisted credentials disabled | Preserve the credential setting; replace the movable tag with a full SHA. |
| 22–25 | setup-uv pinned by SHA; uv 0.12.23; Python 3.12 | Preserve the tool version and the existing action pin. |
| 26 | `uv sync --locked` | Keep the committed lock file; a stale lock must fail. |
| 27–29 | Preflight and Ruff checks | Keep them and put style before expensive checks. |
| 30–31 | Only pytest `infra` and `lab1` selections | Exercise and API tests are omitted. Run the complete suite instead. |

There are no explicit skip conditions or allowed-failure settings in the
original workflow. Later steps naturally stop after an earlier failure;
that is different from never selecting some test files.

## Packaging finding

The archive has no `artifacts/` files because that directory is ignored by
Git. The Dockerfile nevertheless contains `COPY artifacts ./artifacts`.
A fresh checkout therefore needs an explicit model source before building.

The proposed CI prepares a clearly labelled synthetic fixture on its own
runner and retains the existing Dockerfile. The fixture is not the approved
baseline and will not be used by the separate release workflow.

## Proposed coverage and boundaries

- All PRs, main pushes, and manual runs start the same checks.
- A read-only token, pinned actions, bounded jobs and disabled persisted Git
  credentials preserve the safe setup. Telemetry is explicitly disabled.
- Checks runs locked install, lint, format, preflight and all discovered tests.
- Container depends on Checks; it builds, tests and starts the same image,
  then calls the Lab 5 checker over loopback HTTP.
- The expected model version is derived from the known fixture/source before
  requests are sent, not copied from the response being checked.
- Evidence is saved even after failure without suppressing a failing exit.
- The workflow does not claim a recorded-baseline recomputation, completed
  independent defect drill, Cloud Run deployment, or release tag.

## Verification record

The proposed files were checked in an extracted copy of the supplied archive,
using Python 3.12.14, uv 0.12.23 and the unchanged `uv.lock`. MLflow telemetry
was disabled. These are local preparation results, not GitHub runner evidence:

| Check | Observed result |
| --- | --- |
| Ruff lint and formatting | Passed; 15 Python files already formatted. |
| Preflight | Passed imports, frozen snapshot and writable-output checks. |
| Complete pytest suite | 73 passed, 1 existing SQLAlchemy/MLflow deprecation warning, 15.42 seconds. |
| Official actionlint 1.7.12 | Passed workflow validation. |
| Workflow policy and shell syntax | Passed pinned-action, read-only permission, timeout, locked-command and dependency checks; all 14 Bash blocks parsed. |
| Synthetic fixture probes | Prediction 42.0, metadata and model hash matched; a non-empty output directory and invalid SHA were rejected. |
| HTTP from a separate process | Uvicorn on loopback with the generated fixture: the existing checker passed health, prediction, model/code identity and invalid-hour validation; exit 0. |

Docker is unavailable in the preparation environment. No Docker build,
inside-image test, GitHub Actions run or cloud deployment is claimed here.
Those results must be recorded after they actually run on the submitted
revision. The final test count may increase when the tests owner adds the
Phase 2 regressions.
