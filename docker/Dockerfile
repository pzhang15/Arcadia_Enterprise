FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*
RUN pip install uv

WORKDIR /app

COPY vendor/mirage/python/pyproject.toml vendor/mirage/python/uv.lock /app/vendor/mirage/python/
COPY vendor/mirage/python/mirage /app/vendor/mirage/python/mirage

COPY pyproject.toml /app/
COPY packages/eval/pyproject.toml /app/packages/eval/
COPY packages/lineage/pyproject.toml /app/packages/lineage/
COPY packages/catalog-proxy/pyproject.toml /app/packages/catalog-proxy/
COPY packages/credential-broker/pyproject.toml /app/packages/credential-broker/
COPY packages/policy/pyproject.toml /app/packages/policy/
COPY packages/workspace-vfs/pyproject.toml /app/packages/workspace-vfs/
COPY packages/store/pyproject.toml /app/packages/store/

WORKDIR /app/packages/eval
RUN uv sync --no-dev

COPY packages/eval /app/packages/eval
COPY packages/lineage /app/packages/lineage
COPY packages/catalog-proxy /app/packages/catalog-proxy
COPY packages/credential-broker /app/packages/credential-broker
COPY packages/policy /app/packages/policy
COPY packages/workspace-vfs /app/packages/workspace-vfs
COPY packages/store /app/packages/store
RUN uv sync --no-dev

WORKDIR /app
RUN uv sync --no-dev

COPY docker/mock_server.py /app/docker/mock_server.py
COPY docker/generate_traces.py /app/docker/generate_traces.py

RUN uv run --directory /app/packages/eval mirage-eval seed --scenario onboarding_it
RUN uv run --directory /app/packages/eval mirage-eval seed --scenario northhill_corp

WORKDIR /app
EXPOSE 3000 8080 8081
