FROM python:3.12-slim

RUN pip install uv

WORKDIR /app

COPY vendor/mirage/python/pyproject.toml vendor/mirage/python/uv.lock /app/vendor/mirage/python/
COPY vendor/mirage/python/mirage /app/vendor/mirage/python/mirage

COPY pyproject.toml /app/
COPY packages/lineage/pyproject.toml /app/packages/lineage/

WORKDIR /app/packages/lineage
RUN uv sync --no-dev

COPY packages/lineage /app/packages/lineage
RUN uv sync --no-dev

COPY docker/trace-demo/generate_traces.py /app/generate_traces.py

WORKDIR /app
CMD ["uv", "run", "--directory", "/app/packages/lineage", "python", "/app/generate_traces.py"]
