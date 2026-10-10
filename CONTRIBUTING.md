# CONTRIBUTING.md

## Branch + commit naming

- Branch format: lab-XX-<short-description> (example: lab-01-workflow).
- Commit format: imperative, short, in English (example: Normalize team labels).
- One logical change per commit.

## Local checks

Run before opening a pull request:

- `uv run --locked ruff check .`
- `uv run --locked ruff format --check .`
- `uv run --locked pytest -q -m infra`
- `uv run --locked pytest -q -m lab1`

## PR + peer review

- Open a pull request from the task branch into main.
- The reviewer must be a different member (no self-approval).
- The reviewer inspects the diff against the contract and challenges the added test.
- The reviewer records at least one actionable observation.
- The author responds to the observation.
- Checks must be green on the same revision that will be merged.

## Who merges and when

- After the reviewer confirms the change is good and the checks pass on the checked revision, any team member may merge the pull request.
- The merge must be manual.
- Do not merge if a check is failing or a blocker is unresolved.