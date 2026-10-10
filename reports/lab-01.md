# Lab 1: Team workflow and check record

Record observed facts or blocked/not-run with reasons. This team worksheet is
not an individual's graded Week 1 report.

## Team and setup

- Team/repository: mlops-fri2-alna-bike-demand
- Week/date: Week 1 -09/10/2026
- Members and temporary roles:

**Lead:** BoutalebAnas, 

**Reviewer:** nouhasentir

**Members:** Laroche22, Wanying0421

- Repository/authentication access checks: All members invited. Instructor (minhtc-uca) invited on each private report repository.
- Mac version/architecture, Python and uv versions: Python 3.12.1, uv 0.12.24 
- Environment/preflight command and actual outcome: uv run --locked python -m bike_demand.preflight, outcome : Preflight passed: imports, frozen snapshot and writable outputs.
- Working agreement and backlog links: [WORKING-AGREEMENT.md](../WORKING-AGREEMENT.md), [BACKLOG.md](../BACKLOG.md)
- Ignored outputs and secret-protection checks: artifacts/, tracking/ and .venv/ are ignored by Git. No tokens, passwords or personal data in commits or screenshots.

## Reviewed change and checks

- Branch, pull request and checked commit: Branch `lab-01-workflow`, PR #1 into `main`, checked commit `41523de`
- Substantive change and responsible contributor: Fixed `normalize_team_slug` in `src/bike_demand/team.py` to handle `None`, trim whitespace, collapse all whitespaces into one hyphen, lowercase the result, and reject blank names with `ValueError`. Contributor: BoutalebAnas.
- Additional test and why it is useful: test_normalize_team_slug_rejects_none` protects against `AttributeError` when `None` is passed. The contract requires `ValueError` for blank names.
- Reviewer observation, response and merge status: Reviewer (nouhasentir) confirmed the fix satisfies the contract and `pytest -m lab1` passes (4 passed). Formatting was flagged by `ruff format --check`. Response: ran `uv run --locked ruff format .` : nothing to change (10 files already formatted). Merge status: **merged** by Wanying0421 into `main`.
- Local lint/format/test commands and actual results: ________
- Intentional exercise failure versus infrastructure failures: 

`uv run --locked ruff check .` : All checks passed!
`uv run --locked ruff format --check .` : all files already formatted
`uv run --locked pytest -q -m infra` : 9 passed, 38 deselected
`uv run --locked pytest -q -m lab1` : 4 passed

Intentional: "test_joins_whitespace_with_hyphens" failed before the fix. Infrastructure: no failures (`pytest -m infra` passed immediately).

- CI check names, actual statuses and checked revision: `ruff check` passed, `pytest -m infra` passed, `pytest -m lab1` passed on commit `41523de`.
- Starter/reference/collaborator/other assistance: Starter code provided by instructor. Team members helped each other on the diagnostic and the review.

## Lab 2 handover

- Next driver/reviewer: Lead: Wanying0421, Reviewer: BoutalebAnas.
- Readiness and remaining blockers: No blockers. Repository, workflow and quality checks are in place. Lab 2 will use the approved data/training extension.
- One bounded next action and owner: ________
- Own-contribution links retained for each student's Week 1 report: Each member keeps their own commit/PR links and screenshots in their private report repository (`mlops-fri2-<github-username>`).

## Screenshots

Save images in `reports/images/` and embed them below, for example
`![PR checks on a1b2c3d](images/lab-01-pr-checks.png)`. Add one line saying what each
image shows and which commit or pull request it belongs to. Include at least the
failing and the passing `lab1` run, and the pull request checks. Crop to the
relevant part and hide tokens, passwords and personal data.

- Image and caption: 

