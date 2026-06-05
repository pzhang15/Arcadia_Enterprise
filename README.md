# Arcadia

**An experimental platform exploring end-to-end [Mirage](https://github.com/strukto-ai/mirage) capabilities in real-world enterprise scenarios.**

Arcadia is a reference implementation and testing ground built on top of the Mirage virtual filesystem. It exercises Mirage's full surface area — agent integration, data source mounting, workspace execution, observability, and multi-service orchestration — by simulating realistic enterprise environments where AI agents navigate cross-departmental data.

This project does not replace or compete with Mirage. It extends it. Mirage provides the VFS primitives; Arcadia wires them into a governed, observable stack that demonstrates what production Mirage deployments look like when agents need to work across Slack threads, IT tickets, finance records, PagerDuty incidents, and compliance audits simultaneously.

## Why this exists

Mirage gives agents a powerful filesystem abstraction over any data source. But building confidence in that abstraction requires testing it against messy, interconnected, real-world data — the kind where a PagerDuty incident references a deployment, which references a commit, which caused customer escalations, which appear in Slack threads and support tickets.

Arcadia provides that testing surface:

- **End-to-end Mirage validation** — exercises `Workspace`, `DiskResource`, custom `FakeResource` subclasses, `execute()`, `MountMode`, and the observation pipeline against 11 concurrent mount points.
- **Agent integration testing** — runs real LLM agents (OpenAI, Kimi, any OpenAI-compatible provider) through Mirage workspaces via MCP and direct execution, measuring correctness, efficiency, and cost.
- **Enterprise simulation** — 28 employees, 10 Slack channels, 6 departments, 140+ cross-referenced data files spanning IT, HR, Finance, Engineering, Customer Support, and Legal/Compliance.
- **Observability stack** — real-time command tracing, mount-level I/O tracking, and hierarchical span waterfalls showing exactly how agents interact with the VFS.

Everything feeds back into making Mirage better by surfacing edge cases, performance characteristics, and integration patterns that only emerge at scale.

## Architecture (layered on Mirage)

```
┌─────────────────────────────────────────────────────────────┐
│  Agent Sandbox (E2B, Modal, Firecracker, etc.)              │
│                                                             │
│   Agent (any framework, any language)                       │
│     │                                                       │
│     ▼                                                       │
│   /workspace/                          ← Virtual Filesystem │
│     ├── analytics/customers/.schema                         │
│     ├── jira/sprints/.sample                                │
│     ├── slack/channels/                                     │
│     ├── .manifest                                           │
│     ├── .relationships                                      │
│     └── _output/                                            │
│     │                                                       │
│     ▼                                                       │
│   ┌───────────────┐  ┌──────────────┐  ┌────────────────┐  │
│   │ Catalog Proxy │  │ Policy Engine│  │ Lineage Emitter│  │
│   │               │  │              │  │                │  │
│   │ Iceberg       │  │ Column ACL   │  │ OpenLineage    │  │
│   │ Snowflake     │  │ Row filters  │  │ events for     │  │
│   │ PostgreSQL    │  │ Compute      │  │ every read,    │  │
│   │ MCP (Jira,    │  │ budgets      │  │ write, query   │  │
│   │  Slack, etc.) │  │              │  │                │  │
│   │ S3/GCS        │  │              │  │                │  │
│   └───────┬───────┘  └──────────────┘  └────────────────┘  │
│           │ virtio-vsock                                    │
└───────────┼─────────────────────────────────────────────────┘
            ▼
   ┌──────────────────┐
   │ Credential Broker │  ← Host-side, outside sandbox
   │                    │
   │ Short-lived tokens │
   │ Scoped per-task    │
   │ No long-lived      │
   │ creds in sandbox   │
   └──────────────────┘
            │
            ▼
   Enterprise Data Sources
   (Snowflake, Iceberg, PostgreSQL, Jira, Slack, S3, ...)
```

## Key principles (enabled by Mirage)

- **Discovery through navigation.** Mirage's virtual filesystem lets agents explore a directory tree instead of receiving thousands of tokens of tool definitions upfront.
- **Governance by construction.** Policy enforcement happens at the VFS layer. If column X is denied, the mount physically does not return data for it. No prompt override, no code path around it.
- **Credentials never enter the sandbox.** The broker issues short-lived, scoped tokens through a hypervisor channel. A fully compromised agent finds only an ephemeral token that expires in minutes.
- **Lineage is complete by construction.** Every data access goes through Mirage's workspace. There is no path that bypasses it.

## Repo layout

```
arcadia/
├── packages/                 # Independent Python packages (uv workspace)
│   ├── eval/                 # Eval harness — simulated enterprise scenarios
│   ├── catalog-proxy/        # Translates VFS requests to data source APIs
│   ├── credential-broker/    # Host-side token issuance via virtio-vsock
│   ├── lineage/              # OpenLineage event capture for every access
│   ├── policy/               # Column ACL, row filters, compute budgets
│   └── workspace-vfs/        # Dot-file metadata, query.json, output registration
├── frontends/
│   └── platform/             # Unified React app (Portal + Console + Observability)
├── vendor/mirage/            # Upstream Mirage VFS (git subtree from strukto-ai/mirage)
├── docker/                   # Docker compose for the full stack
└── pyproject.toml            # Workspace root
```

## Quick start

```bash
uv sync
cp .env.example .env          # add your OPENAI_API_KEY

# Seed scenario data (once)
uv run mirage-eval seed --scenario northhill_corp

# Option A — production-like Docker stack (no hot reload)
cd docker && docker compose up --build
# → open http://localhost:8080

# Option B — development with hot reload (recommended for UI work)
# see "Development with hot reload" below
# → open http://localhost:5173
```

## Docker stack

### Prerequisites

- Docker and Docker Compose installed
- `uv` installed (`pip install uv`)
- Node.js 22+ (only needed for local frontend hot reload)
- Ports 3000, 5173, 8080–8081 available
- Copy and edit env: `cp .env.example .env`

### Production (built UI, no hot reload)

Builds the React app into `dist/` and serves everything from the platform API on port 8080.

```bash
uv sync
uv run mirage-eval seed --scenario northhill_corp
uv run mirage-eval seed --scenario onboarding_it   # optional second scenario
cd docker && docker compose up --build
```

Open **http://localhost:8080**.

| Service          | Port | URL                         | Purpose                                                  |
| ---------------- | ---- | --------------------------- | -------------------------------------------------------- |
| arcadia-platform | 8080 | http://localhost:8080       | Unified UI + API (Portal + Console + Observability)      |
| mock-services    | 3000 | http://localhost:3000       | Mock HTTP APIs (Slack, GitHub, Jira, PagerDuty, Datadog) |
| mirage           | 8081 | http://localhost:8081/mcp   | MCP server over Streamable HTTP                          |

Rebuild the UI after frontend changes:

```bash
cd frontends/platform && npm run build
cd docker && docker compose up --build arcadia-platform
```

### Development with hot reload

Use this when iterating on the platform UI or API. The React app runs through Vite (port **5173**) with HMR; the FastAPI backend reloads on Python file changes (port **8080**).

There are two ways to run dev mode:

#### Option 1 — Hybrid (recommended)

Docker runs mock services + MCP; backend and frontend run on the host with hot reload.

**Terminal 1 — backing services in Docker:**

```bash
cd docker
docker compose -f docker-compose.services.yml up --build
```

**Terminal 2 — platform API + UI (one command, recommended):**

```bash
uv sync
cd frontends/platform && npm install && npm run dev:all
```

The platform API auto-seeds `northhill_corp` fixture data on first start if the disk tree is missing. To re-seed manually: `uv run mirage-eval seed --scenario northhill_corp`.

`dev:all` starts the API on `:8080`, waits until `/api/health` responds, then starts Vite. The UI proxy targets `127.0.0.1:8080` (avoids IPv6 `ECONNREFUSED` on macOS).

Or run API and UI in separate terminals:

```bash
# from repo root — starts API with reload limited to frontends/platform
./scripts/run-platform-api.sh
```

If you see `Address already in use`, stop the old API first:

```bash
./scripts/stop-platform-api.sh
```

Equivalent manual uvicorn (must pass `--reload-dir` or it watches the whole repo):

```bash
uv run uvicorn server:app --reload --host 0.0.0.0 --port 8080 \
  --app-dir frontends/platform --reload-dir frontends/platform
```

```bash
cd frontends/platform && npm run dev
```

Open **http://localhost:5173**. Vite proxies `/api`, `/events`, and `/ingest` to the backend on `:8080`.

Optional — generate traces for the Trace Timeline view:

```bash
uv run python docker/generate_traces.py
TRACES_DB=data/traces.db RELOAD=1 uv run python frontends/platform/server.py
```

#### Option 2 — All services in Docker with hot reload

Everything runs in containers; source files are volume-mounted so edits still hot reload.

```bash
uv sync
uv run mirage-eval seed --scenario northhill_corp   # once
cd docker
docker compose -f docker-compose.dev.yml up --build
```

Open **http://localhost:5173** (Vite dev server). The API is on **http://localhost:8080** (health checks, direct API testing).

| Dev service   | Port | Hot reload                         |
| ------------- | ---- | ---------------------------------- |
| platform-ui   | 5173 | Vite HMR (`frontends/platform/src`) |
| platform-api  | 8080 | uvicorn `--reload` on `server.py`  |
| mock-services | 3000 | restart container to pick up changes |
| mirage        | 8081 | restart container to pick up changes |

### Health checks

```bash
curl -sf http://localhost:8080/api/health
curl -sf http://localhost:3000/health
```

### Verify seed data

```bash
curl -s http://localhost:8080/api/tickets/it-helpdesk | python3 -m json.tool | head -20
curl -s http://localhost:8080/api/finance/expenses | python3 -m json.tool | head -20
curl -s http://localhost:8080/api/engineering/incidents | python3 -m json.tool | head -20
curl -s http://localhost:8080/api/customers/accounts | python3 -m json.tool | head -20
curl -s http://localhost:8080/api/compliance/contracts | python3 -m json.tool | head -20
```

### Teardown

```bash
cd docker && docker compose down -v
```

## Persistence

Agent activity is durable and survives restarts. The platform persists, and rehydrates on reload:

- **Sessions, chat history, and the full AG-UI event log** — including streamed **reasoning/thinking** (`THINKING_*` events), text, tool calls, steps, runs, and VFS operations. Reloading or restarting the server replays a session's trace from the store.
- **Investigations** — server-persisted and shared across browsers (previously browser-`localStorage` only).
- **The live trace event stream** (`/ingest` → `/events`) — durable and replayable on reconnect via `GET /events?after=<seq>`.
- **Console workspaces** — metadata, captured effects, promoted keys, and snapshots survive restarts. The live mirage workspace is rebuilt lazily on the next operation; RAM-overlay writes made since the last snapshot are not recoverable (surfaced in the workspace status).
- **Eval scorecards** — the harness writes scorecards through to the store (in addition to JSON files); the results API reads DB-first and falls back to files.

### Storage backend

Persistence lives in the `arcadia_store` package (`packages/store`) behind one async store interface (SQLAlchemy 2.0), with two backends selected by `DATABASE_URL`:

- **SQLite** (default) — zero-config for local dev and tests. Defaults to `sqlite+aiosqlite:///<repo>/.arcadia/arcadia.db`.
- **PostgreSQL** — used by the Docker stack (a `postgres:16` service). The schema is created automatically on startup.

This is separate from the read-only `traces.db` produced by `trace-generator` (the lineage span demo for the Trace Timeline) — that remains an independent immutable SQLite file at `TRACES_DB`.

To run the host API (hybrid dev) against the dockerized Postgres (published on `localhost:5432` by `docker-compose.services.yml`):

```bash
DATABASE_URL=postgresql+asyncpg://arcadia:arcadia@localhost:5432/arcadia \
  uv run uvicorn server:app --app-dir frontends/platform --host 0.0.0.0 --port 8080
```

### Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite+aiosqlite:///<repo>/.arcadia/arcadia.db` | Async store DSN (SQLite or `postgresql+asyncpg://…`). |
| `OPENAI_REASONING` | `1` (on) | Capture model reasoning as `THINKING_*` events (native `reasoning_content` plus a `<thinking>…</thinking>` fallback). |
| `STREAM_EVENT_RETENTION_MAX` | `200000` | Max relay `stream_events` rows retained (older rows pruned periodically). |
| `STORE_FLUSH_INTERVAL` | `2.0` | Seconds between background flushes of buffered events to the store. |
| `CONSOLE_SNAP_DIR` | system temp dir | Directory for console workspace snapshot tarballs (mount a volume to persist them). |

## Running tests

### Backend (Python)

```bash
uv run pytest                                                        # all tests
uv run pytest packages/eval/scenarios/northhill_corp/tests/ -v       # northhill_corp tests
uv run pytest packages/lineage/tests/ -v                             # lineage tests
uv run pytest frontends/platform/tests/ -v                           # Mirage Console API integration suite
```

The Console integration suite stands up real Mirage workspaces through the platform API and
exercises every weak link end to end — create/stand-up, mount permission enforcement, the
testing-agent dispatch, SSE traces, overlay/effects/trajectory derivation, simulated promote,
branch/snapshot/reset, and teardown.

### Frontend (TypeScript)

```bash
cd frontends/platform
npm test                    # watch mode
npm run test:run            # single run
npm run test:coverage       # with coverage report
```

### Linting

```bash
pre-commit run --all-files
```

## Platform UI

**Production / built UI:** http://localhost:8080  
**Development (hot reload):** http://localhost:5173

The unified platform combines three sections:

**Portal** — simulated enterprise department tools:

| Department       | What it shows                                                   |
| ---------------- | --------------------------------------------------------------- |
| IT Helpdesk      | Ticket queue (ServiceNow-style), filterable by status/priority  |
| HR & People      | Employee directory, onboarding tracker, PTO calendar            |
| Finance          | Expense report queue, purchase orders, department budgets       |
| Engineering      | Active incidents, deployment log, monitoring alerts             |
| Customer Support | Support tickets (Zendesk-style), account health cards           |
| Compliance       | Contract review queue, audit checklists, policy acknowledgments |

**Console** — interactive AI agent workspace. Select departments, describe a task, watch the agent work.

**Observability** — real-time agent monitoring:

| View             | What it shows                                                                         |
| ---------------- | ------------------------------------------------------------------------------------- |
| Command Timeline | Live stream of every `execute()` call — command, exit code, timing, stdout, mount I/O |
| MCP Traffic      | JSON-RPC request/response pairs for the MCP protocol layer                            |
| Request Log      | HTTP requests hitting the mock backend services, filterable by service                |
| Resource Map     | Which mounts the agent touched, read/write counts, bytes transferred                  |
| Trace Explorer   | Hierarchical span waterfall for every VFS operation                                   |
| Scorecard        | Eval results — composite scores, gate pass/fail, judge rubric, failure modes          |

### Mirage Console (developer dev→test→promote loop)

A second, developer-facing front door at **`/console`** for dogfooding Mirage itself: stand up a
workspace, run an agent against virtualized state, and decide what reaches the real world. The
captured-vs-real boundary is the central visual — every mutation is badged `CAPTURED` (in overlay,
reversible), `SIMULATED` (external effect faked, not sent), or `LIVE` (committed, irreversible).

| Surface    | What it does                                                                                     |
| ---------- | ------------------------------------------------------------------------------------------------ |
| Workspaces | Create from a template or `workspace.yaml`, stand up with a provision dry-run, branch, tear down  |
| Run        | Drive an agent — or dispatch the built-in **testing agent** — and watch the overlay fill live     |
| Trajectory | Unified, filterable read/write/effect timeline; export as JSON                                     |
| State      | Backing vs. overlay vs. effective per mount; snapshot / branch / reset; branch tree                |
| Promote    | Review captured effects and commit selectively (simulated — see note) with typed confirmation      |

**Testing agent.** On the Run surface, "Test agent" dispatches a deterministic, no-LLM smoke sequence
that probes every mount (writes to writable mounts, reads them back, confirms read-only mounts block
writes) and returns a per-mount permission-enforcement report. The same `POST
/api/console/workspaces/{id}/test-run` endpoint powers the integration suite, so the dev loop and CI
exercise identical wiring.

**Engine honesty.** Branch (`Workspace.copy`), snapshot/reset (`snapshot`/`load`), the capture overlay,
and the unified trajectory map to real Mirage primitives. The engine has no write-back primitive yet,
so **Promote is simulated** — effects are marked promoted and logged, but no real external call is
made; LIVE-mode chrome is present but gated. Deterministic Replay and parallel Compare are deferred.

## Local development (without Docker)

If you only need the platform UI + API against seeded fixture data (no mock HTTP services or MCP):

```bash
uv sync
uv run mirage-eval seed --scenario northhill_corp

# Terminal 1 — API with hot reload
RELOAD=1 uv run python frontends/platform/server.py

# Terminal 2 — UI with hot reload
cd frontends/platform && npm install && npm run dev
```

Open http://localhost:5173. Without Docker, observability events from mock services and MCP will not appear unless you also start the backing services (see hybrid dev mode above).

## Syncing upstream Mirage

Arcadia tracks Mirage as a git subtree. To pull the latest upstream changes:

```bash
git subtree pull --prefix=vendor/mirage upstream main --squash
```

## Relationship to Mirage

Arcadia depends on [Mirage](https://github.com/strukto-ai/mirage) and would not exist without it. The relationship is:

- **Mirage** provides the virtual filesystem core — workspace creation, resource mounting, shell command execution, observation recording, and the MCP server transport.
- **Arcadia** provides the enterprise integration layer — synthetic data generation, multi-department scenarios, agent evaluation, a governance stack (policy, lineage, credential broker), and a full-stack UI for visualization and interactive agent sessions.

Bugs and patterns discovered in Arcadia flow upstream as issues and contributions to Mirage. Arcadia's eval harness serves as an integration test suite for Mirage's workspace API across diverse, concurrent mount configurations.

## Roadmap

| Phase | Sources                                                 | Timeline     |
| ----- | ------------------------------------------------------- | ------------ |
| MVP   | Iceberg, Snowflake, PostgreSQL, Jira, S3/GCS            | Months 1–9   |
| v1.1  | Delta Lake, Salesforce, GitHub, Google Workspace, MySQL | Months 9–12  |
| v1.2  | BigQuery, MongoDB, Vector Stores, Slack, Confluence     | Months 12–18 |
| v2    | Hudi, DynamoDB, ServiceNow, Datadog, Elasticsearch      | Months 18+   |
