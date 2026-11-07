# Member 1 local verification

These records were produced in a local Linux environment from the supplied
archive plus the Member 1 changes. They are **not** GitHub runner, Windows,
Docker-build, gate-decision or Cloud Run evidence.

`source.json` identifies the input archive and its recorded Git commit. The
source was extracted without its original Git history. No real course candidate
was trained or evaluated in this preparation. Training tests use six synthetic
rows and a separate synthetic Git repository; their lock is a labelled fixture.

| Command / check | Observed result | Raw record |
| --- | --- | --- |
| `uv sync --locked` | Passed; existing lock retained | `install.txt` |
| `uv run --locked ruff check .` | Passed | `lint.txt` |
| `uv run --locked ruff format --check .` | Passed | `format.txt` |
| `uv run --locked python -m bike_demand.preflight` | Passed | `preflight.txt` |
| `uv run --locked python -m bike_demand.pipeline check --config configs/baseline.yaml` | Validated 8,645 / 4,358 / 4,376 rows; no model or scores | `input-check.json` |
| `uv run --locked pytest -q` | 84 passed, 1 existing SQLAlchemy/MLflow deprecation warning | `pytest.txt` |

The archive's unmodified suite passed 74 tests before the change. The ten new
tests cover train-only fitting, unchanged accepted files and reports, complete
bundle identities, ID collisions, incomplete fit, mid-run input mutation,
uncommitted source, invalid model parameters and output path traversal.

`verified-files.json` records hashes of the changed implementation/configuration
files associated with these local checks. Preserve raw text/JSON bytes using the
repository's `.gitattributes` rules. The records include their own Linux paths
and timing; do not relabel them as a teammate's Windows run.

The two CI verification jobs are retained, but this environment has no Docker
executable. The actual PR must run `Checks` and `Container` successfully on its
own revision. An independent teammate must review the code and contract before
manual merge. The removed automatic deployment is replaced only when Member 4
implements and proves the reviewed manual promotion workflow.
