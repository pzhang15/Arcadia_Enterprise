# Docker Stack — Setup, Seed Data & Testing Guide

## Prerequisites

- Docker and Docker Compose installed
- `uv` installed (`pip install uv`)
- Ports 3000, 8080–8084 available

## Quick Start (Docker)

From the repo root:

```bash
# 1. Seed all scenarios (writes fixture JSON to disk — needed before Docker build)
cd packages/eval
uv run mirage-eval seed --scenario northhill_corp
uv run mirage-eval seed --scenario northhill_corp
uv run mirage-eval seed --scenario onboarding_it

# 2. Build and start the full stack
cd ../../docker
docker compose up --build
```

Wait for all services to report healthy. The trace generator runs first and prints:

```
Done: 20 traces, ... total spans written to /app/data/traces.db
```

Then the remaining services start in dependency order.

## Services

| Service         | Port | URL                            | Data source        |
|-----------------|------|--------------------------------|--------------------|
| observability   | 8082 | http://localhost:8082           | Trace SQLite + SSE |
| portal          | 8083 | http://localhost:8083           | NorthHill Corp fixture  |
| console         | 8084 | http://localhost:8084           | NorthHill Corp fixture  |
| mock-services   | 3000 | http://localhost:3000           | NorthHill Corp seed |
| mirage-api      | 8080 | http://localhost:8080           | Mirage HTTP daemon |
| mirage-mcp      | 8081 | http://localhost:8081/mcp       | NorthHill Corp MCP  |

## Health Checks

```bash
curl -sf http://localhost:3000/health
curl -sf http://localhost:8082/api/health
curl -sf http://localhost:8083/api/health
curl -sf http://localhost:8084/api/health
```

## Verifying Seed Data

### Portal (NorthHill Corp departments)

```bash
# IT tickets
curl -s http://localhost:8083/api/tickets/it-helpdesk | python3 -m json.tool | head -20

# Employees
curl -s http://localhost:8083/api/employees | python3 -m json.tool | head -20

# Finance
curl -s http://localhost:8083/api/finance/expenses | python3 -m json.tool | head -20
curl -s http://localhost:8083/api/finance/budgets | python3 -m json.tool | head -20

# Engineering
curl -s http://localhost:8083/api/engineering/incidents | python3 -m json.tool | head -20

# Customers
curl -s http://localhost:8083/api/customers/accounts | python3 -m json.tool | head -20

# Compliance
curl -s http://localhost:8083/api/compliance/contracts | python3 -m json.tool | head -20
```

### Trace Explorer

```bash
# Stats
curl -s http://localhost:8082/api/traces/stats/summary | python3 -m json.tool

# List traces
curl -s 'http://localhost:8082/api/traces?limit=5' | python3 -m json.tool | head -30
```

### Mock Services (NorthHill Corp)

```bash
curl -s http://localhost:3000/slack/api/users.list | python3 -m json.tool | head -20
curl -s http://localhost:3000/pagerduty/incidents | python3 -m json.tool | head -20
curl -s http://localhost:3000/finance/expenses | python3 -m json.tool | head -20
```

## Running Tests

### Unit + Integration tests (no Docker needed)

```bash
# From the repo root — run everything
cd packages/eval && uv run pytest

# NorthHill Corp seed + workspace + portal data tests (64 tests)
uv run pytest scenarios/northhill_corp/tests/ -v

# Lineage / trace pipeline tests (67 tests)
cd ../../
uv run pytest packages/lineage/tests/ -v

# All tests together (runs from repo root)
uv run pytest packages/lineage/tests/ packages/eval/ -v
```

### What the tests cover

**Lineage tests** (`packages/lineage/tests/`):

| File | Tests | Coverage |
|------|-------|----------|
| `test_e2e_trace_pipeline.py` | 9 | Full execute → SQLite → API query patterns, WAL checkpoint, cache hits, error traces |
| `test_e2e_observability_server.py` | 14 | Replicates `/api/traces`, `/api/traces/{id}`, `/api/traces/stats/summary` SQL queries |
| `test_tracing_workspace.py` | 9 | TracingWorkspace delegation, span creation, parent-child linkage |
| `test_sqlite_store.py` | 7 | Write/query/count/idempotency for the SQLite store |
| `test_collector.py` | 6 | SpanCollector trace tree building from OpRecords |
| `test_buffer.py` | 8 | Ring buffer tiers, eviction, back-pressure |
| `test_span.py` | 8 | Span/SpanEvent/SpanMetrics construction |
| `test_mirage_ops_contract.py` | 6 | OpRecord field contracts with mirage |

**NorthHill Corp tests** (`packages/eval/scenarios/northhill_corp/tests/`):

| File | Tests | Coverage |
|------|-------|----------|
| `test_seed_completeness.py` | 21 | All departments seeded, JSON validity, idempotency |
| `test_portal_data_serving.py` | 20 | Portal's disk-reading patterns, env var config, Docker wiring |
| `test_mock_server_data.py` | 12 | Mock server data loading, status values, cross-reference integrity |
| `test_workspace_integration.py` | 11 | Full Mirage workspace: ls, cat, find across all 11 mounts |

### Linting

```bash
pre-commit run --all-files
```

## Local Development (Without Docker)

### 1. Seed data

```bash
cd packages/eval
uv run mirage-eval seed --scenario northhill_corp
```

### 2. Start the portal

```bash
cd frontends/portal
pip install fastapi uvicorn httpx
python server.py
# → http://localhost:8083
```

The portal auto-detects seed data at `packages/eval/scenarios/northhill_corp/fixture/disk/`.

### 3. Generate traces + start observability

```bash
# Generate trace data to a local file
uv run python docker/generate_traces.py

# Start the observability relay
cd frontends/observability
pip install fastapi uvicorn httpx
TRACES_DB=/app/data/traces.db python server.py
# → http://localhost:8082

# For hot-reload frontend dev
npm install && npm run dev
# → http://localhost:5173
```

### 4. Start the console (requires OpenAI key)

```bash
cd frontends/console
pip install fastapi uvicorn httpx openai
OPENAI_API_KEY=sk-... python server.py
# → http://localhost:8084
```

## Trace Explorer Walkthrough

After starting the stack, open http://localhost:8082 and click **Trace Explorer** in the sidebar.

1. **Trace list** — 20 traces with command, status (OK/ERR), duration, span count, bytes, cache rate
2. **Click a trace** — waterfall timeline: root span + child I/O spans (read/write/readdir)
3. **Click a span** — detail panel: timing, bytes, cache hits, attributes, span IDs
4. **Error trace** — `cat /data/nonexistent.txt` shows red ERROR badge, non-zero exit code
5. **Cache hits** — last two traces re-read earlier files, child spans show `cache_hit: true` (green bars)

## Teardown

```bash
cd docker
docker compose down -v    # -v removes the trace-data volume
```
