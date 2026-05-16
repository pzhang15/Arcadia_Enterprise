FROM python:3.12-slim

RUN pip install uv

WORKDIR /app

COPY ../python /app/python
COPY . /app/enterprise

WORKDIR /app/enterprise
RUN uv sync --no-dev

RUN uv run mirage-eval seed --scenario meridian_labs

EXPOSE 3000 8080 8081
