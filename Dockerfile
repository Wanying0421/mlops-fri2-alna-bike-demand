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

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-install-project

COPY src ./src
COPY configs ./configs
COPY data ./data
COPY tests ./tests
COPY README.md ./README.md
COPY .github/workflows/ci.yml ./.github/workflows/ci.yml
COPY reports/week-01-team.md ./reports/week-01-team.md

RUN uv sync --locked

ARG VCS_REF=unrecorded
LABEL org.opencontainers.image.source="https://github.com/Wanying0421/mlops-fri2-alna-bike-demand" \
      org.opencontainers.image.revision="${VCS_REF}"

ENV UV_OFFLINE=1

EXPOSE 8000
CMD ["uv", "run", "--locked", "uvicorn", "bike_demand.api:app", "--host", "0.0.0.0", "--port", "8000"]
