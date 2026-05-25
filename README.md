# Arcadia

**The governed intelligence platform for autonomous agents.**

Sandboxes solved isolation. Isolation without governed data access is a sandbox with nothing useful inside it. Arcadia is what makes the sandbox worth booting.

## What we're building

Arcadia gives AI agents governed, discoverable access to enterprise data through a virtual filesystem. The agent runs `ls`, `cat`, and `read` — the same operations every LLM already knows — and Arcadia handles discovery, access control, credential security, and audit trails behind the scenes.

No new SDKs. No custom tool definitions. Works with any agent framework.

## Target architecture

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

## Key principles

- **Discovery through navigation.** Agents explore a directory tree instead of receiving thousands of tokens of tool definitions upfront.
- **Governance by construction.** If the policy says column X is denied, the FUSE layer physically does not return data for column X. No prompt override, no code path around it.
- **Credentials never enter the sandbox.** The broker issues short-lived, scoped tokens through a hypervisor channel. A fully compromised agent finds only an ephemeral token that expires in minutes.
- **Lineage is complete by construction.** Every data access goes through the VFS. There is no path that bypasses it.

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
├── vendor/mirage/            # Upstream mirage VFS (git subtree)
├── docker/                   # Docker compose for the full stack
└── pyproject.toml            # Workspace root
```

## Quick start

```bash
uv sync
cp .env.example .env          # add your OPENAI_API_KEY

# Seed scenario data
uv run mirage-eval seed --scenario northhill_corp

# Start the platform locally
uv run python frontends/platform/server.py    # http://localhost:8080

# Or start everything in Docker
cd docker && docker compose up --build
```

## Docker stack

### Prerequisites

- Docker and Docker Compose installed
- `uv` installed (`pip install uv`)
- Ports 3000, 8080–8081 available

### Start

```bash
uv sync
uv run mirage-eval seed --scenario northhill_corp
uv run mirage-eval seed --scenario onboarding_it
cd docker && docker compose up --build
```

### Services

| Service          | Port | URL                       | Purpose                                                  |
| ---------------- | ---- | ------------------------- | -------------------------------------------------------- |
| arcadia-platform | 8080 | http://localhost:8080     | Unified UI + API (Portal + Console + Observability)      |
| mock-services    | 3000 | http://localhost:3000     | Mock HTTP APIs (Slack, GitHub, Jira, PagerDuty, Datadog) |
| mirage           | 8081 | http://localhost:8081/mcp | MCP server over Streamable HTTP                          |

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

## Running tests

### Backend (Python)

```bash
uv run pytest                                                        # all tests
uv run pytest packages/eval/scenarios/northhill_corp/tests/ -v       # northhill_corp tests
uv run pytest packages/lineage/tests/ -v                             # lineage tests
```

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

The unified platform at http://localhost:8080 combines three sections:

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

## Local development

```bash
# Backend
uv run python frontends/platform/server.py                    # API on :8080

# Frontend hot-reload
cd frontends/platform && npm install && npm run dev            # on :5173 (proxied to :8080)

# Generate traces for Trace Explorer
uv run python docker/generate_traces.py
TRACES_DB=data/traces.db uv run python frontends/platform/server.py
```

## Syncing upstream mirage

```bash
git subtree pull --prefix=vendor/mirage upstream main --squash
```

## Roadmap

| Phase | Sources                                                 | Timeline     |
| ----- | ------------------------------------------------------- | ------------ |
| MVP   | Iceberg, Snowflake, PostgreSQL, Jira, S3/GCS            | Months 1–9   |
| v1.1  | Delta Lake, Salesforce, GitHub, Google Workspace, MySQL | Months 9–12  |
| v1.2  | BigQuery, MongoDB, Vector Stores, Slack, Confluence     | Months 12–18 |
| v2    | Hudi, DynamoDB, ServiceNow, Datadog, Elasticsearch      | Months 18+   |
