# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/models

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl libpq5 \
    && rm -rf /var/lib/apt/lists/*

# --- Dependency layer (cached unless pyproject changes) ---
COPY pyproject.toml README.md ./
RUN python -m pip install --upgrade pip \
    && pip install --extra-index-url https://download.pytorch.org/whl/cpu \
       "torch>=2.2,<3" \
    && pip install ".[dev]"

# --- Application code ---
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./
COPY scripts ./scripts

RUN pip install --no-deps . && useradd -m appuser && mkdir -p /models && chown -R appuser /app /models
USER appuser

EXPOSE 8000

# Default: API server. Compose overrides `command` for the worker service.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
