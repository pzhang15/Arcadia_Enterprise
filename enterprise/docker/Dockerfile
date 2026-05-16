FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*
RUN pip install uv

WORKDIR /app
COPY python /app/python
COPY enterprise /app/enterprise

WORKDIR /app/enterprise
RUN uv sync --no-dev

RUN uv run mirage-eval seed --scenario onboarding_it
RUN uv run mirage-eval seed --scenario meridian_labs

EXPOSE 3000 8080 8081
