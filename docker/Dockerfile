FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*
RUN pip install uv

WORKDIR /app

COPY vendor/mirage/python/pyproject.toml vendor/mirage/python/uv.lock /app/vendor/mirage/python/
COPY vendor/mirage/python/mirage /app/vendor/mirage/python/mirage

COPY pyproject.toml /app/
COPY packages/eval/pyproject.toml packages/eval/uv.lock /app/packages/eval/

WORKDIR /app/packages/eval
RUN uv sync --no-dev

COPY packages/eval /app/packages/eval
RUN uv sync --no-dev

RUN uv run mirage-eval seed --scenario onboarding_it
RUN uv run mirage-eval seed --scenario meridian_labs
RUN uv run mirage-eval seed --scenario acme_corp

EXPOSE 3000 8080 8081
