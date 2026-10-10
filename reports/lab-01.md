# Lab 1: Team workflow and check record

Record observed facts or blocked/not-run with reasons. This team worksheet is
not an individual's graded Week 1 report.

## Team and setup

- Team/repository: https://github.com/Wanying0421/mlops-fri2-alna-bike-demand
- Week/date: Week 1 — 2026-10-10
- Members and temporary roles:
  - Laroche: Repository setup, role identification, and initial bug diagnosis.
  - Anas: Project documentation, code fix, additional test, and Git workflow.
  - Nouha: Local checks, code review, and GitHub check verification.
  - Wanying: Pull request merge, team report, and individual report.
  - Lead author: Anas.
  - Reviewer: Nouha.
- Repository/authentication access checks:
  - All four team members can access the shared GitHub repository.
  - Repository access was established during the initial setup.
  - Pull request #1 was successfully merged into the main branch.
- Mac version/architecture, Python and uv versions: Mac version/architecture, Python and uv versions: Windows (x64), Python 3.10.12, uv 0.12.19
- Environment/preflight command and actual outcome: `uv run --locked python -m bike_demand.preflight` passed successfully for all members.
- Working agreement and backlog links: Documented in README.md, CONTRIBUTING.md, and WORKING-AGREEMENT.md in the repository root.
- Ignored outputs and secret-protection checks: Verified via `.gitignore`; no sensitive credentials or generated artifacts were committed.

## Reviewed change and checks

- Branch, pull request and checked commit: Branch `lab-01-workflow`, Pull Request #1, Checked commit `ff0d9ae`.
- Substantive change and responsible contributor: Fixed `normalize_team_slug` helper function in `src/bike_demand/team.py` by Anas.
- Additional test and why it is useful: Added test case for rejecting `None` and tabs/whitespace in `tests/lab1/test_team.py` by Anas, protecting against invalid edge cases not covered by starter tests.
- Reviewer observation, response and merge status: Nouha reviewed the PR and requested edge-case test coverage; Anas updated the tests; Wanying verified local/remote checks and manually merged PR #1 into `main`.
- Local lint/format/test commands and actual results: 
  - `uv run --locked ruff check` -> Passed
  - `uv run --locked ruff format --check` -> Passed
  - `uv run --locked pytest -q -m infra` -> Passed
  - `uv run --locked pytest -q -m lab1` -> Passed (after fix)
- Intentional exercise failure versus infrastructure failures: `pytest -m lab1` failed initially due to the intentional bug in `normalize_team_slug`; no infrastructure failures occurred.
- CI check names, actual statuses and checked revision: `ruff check`, `pytest -m infra`, and `pytest -m lab1` all reported successful green checks on commit `ff0d9ae`.
- Starter/reference/collaborator/other assistance: Course starter package and team collaboration.

## Lab 2 handover

- Next driver/reviewer: Lead: Wanying, Reviewer: Anas.
- Readiness and remaining blockers: Repository is fully configured, Lab 1 workflow and merge completed successfully, zero blockers.
- One bounded next action and owner: Initiate Lab 2 data split and baseline task, owned by Laroche.
- Own-contribution links retained for each student's Week 1 report: Individual commit and review links recorded in each member's private report.

## Screenshots

## Screenshots
- ![Local pytest passing](images/lab-01-passing-test.jpeg)
  *Local `pytest -m lab1` passing with 4 test cases on branch `lab-01-workflow`.*
- ![Peer review conversation](images/lab-01-peer-review.jpeg)
  *Peer review on PR #1 between Nouha (Reviewer) requesting code formatting and Anas (Author) confirming the fix.*
- ![Initial CI failure](images/lab-01-failing-ci.jpeg)
  *Initial remote CI check failure caused by `ruff format --check` before applying formatting fix.*
- ![Final CI checks passing](images/lab-01-pr-checks.jpeg)
  *Final GitHub Actions checks passing on PR #1 ready for manual merge.*
