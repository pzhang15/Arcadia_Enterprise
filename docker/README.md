# Docker Stack — Setup, Seed Data & Testing Guide

## Prerequisites

- Docker and Docker Compose installed
- `uv` installed (`pip install uv`)
- Ports 3000, 8080–8081 available

## Quick Start (Docker)

All commands run from the repo root:

```bash
# 1. Install dependencies
uv sync

# 2. Seed all scenarios (writes fixture JSON to disk — needed before Docker build)
uv run mirage-eval seed --scenario northhill_corp
uv run mirage-eval seed --scenario onboarding_it

# 3. Build and start the full stack
cd docker && docker compose up --build
```

Wait for all services to report healthy. The trace generator runs first and prints:

```
Done: 20 traces, ... total spans written to /app/data/traces.db
```

Then the remaining services start in dependency order.

## Services

| Service           | Port | URL                      | Purpose                          |
|-------------------|------|--------------------------|----------------------------------|
| arcadia-platform  | 8080 | http://localhost:8080     | Unified UI + API (Portal + Console + Observability) |
| mock-services     | 3000 | http://localhost:3000     | Mock HTTP APIs (Slack, GitHub, Jira, PagerDuty, Datadog) |
| mirage            | 8081 | http://localhost:8081/mcp | MCP server over Streamable HTTP  |

## Health Checks

```bash
curl -sf http://localhost:8080/api/health
curl -sf http://localhost:3000/health
```

## Verifying Seed Data

### Portal (NorthHill Corp departments)

```bash
curl -s http://localhost:8080/api/tickets/it-helpdesk | python3 -m json.tool | head -20
curl -s http://localhost:8080/api/employees | python3 -m json.tool | head -20
curl -s http://localhost:8080/api/finance/expenses | python3 -m json.tool | head -20
curl -s http://localhost:8080/api/engineering/incidents | python3 -m json.tool | head -20
curl -s http://localhost:8080/api/customers/accounts | python3 -m json.tool | head -20
curl -s http://localhost:8080/api/compliance/contracts | python3 -m json.tool | head -20
```

### Trace Explorer

```bash
curl -s http://localhost:8080/api/traces/stats/summary | python3 -m json.tool
curl -s 'http://localhost:8080/api/traces?limit=5' | python3 -m json.tool | head -30
```

### Mock Services (NorthHill Corp)

```bash
curl -s http://localhost:3000/slack/api/users.list | python3 -m json.tool | head -20
curl -s http://localhost:3000/pagerduty/incidents | python3 -m json.tool | head -20
```

## Running Tests

All commands from the repo root:

```bash
# Run everything
uv run pytest

# NorthHill Corp seed + workspace + portal data tests (64 tests)
uv run pytest packages/eval/scenarios/northhill_corp/tests/ -v

# Lineage / trace pipeline tests (67 tests)
uv run pytest packages/lineage/tests/ -v

# All tests together
uv run pytest packages/lineage/tests/ packages/eval/ -v
```

### What the tests cover

**Lineage tests** (`packages/lineage/tests/`):

| File | Tests | Coverage |
|------|-------|----------|
| `test_e2e_trace_pipeline.py` | 9 | Full execute -> SQLite -> API query patterns, WAL checkpoint, cache hits, error traces |
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

All commands from the repo root.

### 1. Seed data

```bash
uv run mirage-eval seed --scenario northhill_corp
```

### 2. Start the unified platform

```bash
uv run python frontends/platform/server.py
# -> http://localhost:8080
```

### 3. Frontend hot-reload dev

```bash
cd frontends/platform && npm install && npm run dev
# -> http://localhost:5173
```

### 4. Generate traces

```bash
uv run python docker/generate_traces.py
TRACES_DB=/app/data/traces.db uv run python frontends/platform/server.py
```

## Trace Explorer Walkthrough

After starting the stack, open http://localhost:8080 and click **Trace Explorer** in the Observability section.

1. **Trace list** -- 20 traces with command, status (OK/ERR), duration, span count, bytes, cache rate
2. **Click a trace** -- waterfall timeline: root span + child I/O spans (read/write/readdir)
3. **Click a span** -- detail panel: timing, bytes, cache hits, attributes, span IDs
4. **Error trace** -- `cat /data/nonexistent.txt` shows red ERROR badge, non-zero exit code
5. **Cache hits** -- last two traces re-read earlier files, child spans show `cache_hit: true` (green bars)

## Teardown

```bash
cd docker && docker compose down -v    # -v removes the trace-data volume
```
