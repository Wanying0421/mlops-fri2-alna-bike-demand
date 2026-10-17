FROM python:3.12.14-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e

COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /uvx /usr/local/bin/
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_NO_CACHE=1 \
    UV_LINK_MODE=copy \
    MLFLOW_DISABLE_TELEMETRY=true \
    DO_NOT_TRACK=true

# The existing tracking code calls git, even when .git is absent.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Keep the dependency layer reusable when only application code changes.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-install-project

COPY src ./src
COPY configs ./configs
COPY data ./data
COPY tests ./tests
COPY README.md ./README.md
COPY .github/workflows/ci.yml ./.github/workflows/ci.yml
COPY reports/week-01-team.md ./reports/week-01-team.md

# Retain dev dependencies: the same image must also run pytest and Ruff.
RUN uv sync --locked

ARG VCS_REF=unrecorded
LABEL org.opencontainers.image.source="https://github.com/Wanying0421/mlops-fri2-alna-bike-demand" \
      org.opencontainers.image.revision="${VCS_REF}"

# A run must use the installed environment without downloading anything.
ENV UV_OFFLINE=1
CMD ["uv", "run", "--locked", "python", "-m", "bike_demand.train", "--config", "configs/baseline.yaml"]
