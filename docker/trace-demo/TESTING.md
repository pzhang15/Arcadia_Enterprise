# Trace Explorer — End-to-End Testing Guide

This guide walks you through building, running, and visually inspecting the hierarchical tracing system from end to end.

## Prerequisites

- Docker and Docker Compose installed
- Ports 8082 available

## Quick Start (Docker)

From the repo root:

```bash
cd docker/trace-demo
docker compose up --build
```

This does two things:

1. **trace-generator** — Builds and runs 20 demo commands through `TracingWorkspace`, writing hierarchical spans to `/app/data/traces.db` (SQLite)
2. **observability** — Starts the Observability UI on port 8082, pointing at the same SQLite file

Once you see `Done: 20 traces, ... total spans written`, the UI is ready.

Open **http://localhost:8082** in your browser.

## Step-by-Step Walkthrough

### Step 1: Navigate to Trace Explorer

In the left sidebar, click **Trace Explorer** under the "Traces" section.

You should see:
- Stats cards showing total traces and total spans
- A table listing all 20 traces, each with: timestamp, command, status (OK/ERR), duration, span count, bytes, and cache hit rate

**What to verify:**
- All 20 traces are listed
- One trace shows ERR status (the `cat /data/nonexistent.txt` command)
- Duration values look reasonable (sub-second)
- Span counts are > 1 (root span + child I/O spans)

### Step 2: Inspect a Trace (Waterfall View)

Click any row in the trace table (try `cat /data/logs/app.log`).

You should see:
- A **waterfall timeline** showing the root `execute` span at the top
- Child spans indented below, each representing an I/O operation (read, write, readdir)
- Horizontal bars showing relative timing
- Color coding: blue = root, cyan = cache miss, green = cache hit, red = error

**What to verify:**
- The root span spans the full width
- Child spans (read operations) are nested under the root
- Bar widths reflect actual timing proportions
- The time ruler at the top shows the trace duration range

### Step 3: Inspect a Span (Detail Panel)

Click on any span in the waterfall to open the detail panel on the right.

You should see:
- **Timing section** — duration, start/end timestamps
- **Metrics section** — bytes read/written, API calls, cache hits/misses, hit rate
- **Attributes section** — operation type, path, source, mount prefix, cache hit boolean
- **Span IDs** — trace_id, span_id, parent_span_id (truncated)

**What to verify:**
- Root span attributes show the full command string and exit code
- Child span attributes show the specific I/O operation (e.g., `op: read`, `path: /data/logs/app.log`)
- Cache hit boolean reflects whether the data was served from RAM cache
- Bytes values match expected sizes

### Step 4: Inspect an Error Trace

Go back to the trace list and click the trace with ERR status (`cat /data/nonexistent.txt`).

**What to verify:**
- Root span shows red "ERROR" badge
- Exit code in attributes is non-zero
- The waterfall bar is red
- No child I/O spans (the read failed before producing any)

### Step 5: Observe Cache Hits

Later traces (e.g., re-reading `/data/incident.txt` after it was written) may show cache hits.

**What to verify:**
- Child spans for cached reads show `cache_hit: true` in attributes
- The span bar is green for cache hits
- Root span metrics show cache_hits > 0

## Local Development (Without Docker)

If you prefer to run things locally:

### 1. Generate traces

```bash
cd /path/to/Arcadia_Enterprise
uv run python docker/trace-demo/generate_traces.py
```

This creates `traces.db` at `/app/data/traces.db`. Override the path by editing the script's `DB_PATH`.

### 2. Start the observability server

```bash
cd frontends/observability
TRACES_DB=/path/to/traces.db python server.py
```

### 3. Start the Vite dev server (for hot-reload during development)

```bash
cd frontends/observability
npm install
npm run dev
```

Open **http://localhost:5173** — the Vite dev server proxies API calls to the Python server on 8082.

## Teardown

```bash
cd docker/trace-demo
docker compose down -v
```

The `-v` flag removes the `trace-data` volume.
