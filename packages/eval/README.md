# Arcadia Eval — Governed AI Workspaces for Heterogeneous Enterprise Environments

This is the `packages/eval` component of the [Arcadia](../../README.md) platform.

It simulates realistic enterprise environments where AI agents navigate cross-domain data under workspace-level governance — the same filesystem abstraction, the same observation pipeline, and the same scoring framework that would run in production, but backed by synthetic seed data so you can iterate without credentials, without cost, and without risk.

What you get:

- **Simulated enterprise scenarios** with coherent, cross-referenced data across 13 services (Slack, ITSM, GitHub, PagerDuty, Datadog, GSheets, GDocs, Finance, CRM, Compliance, Database, S3). Every ticket references a deployment, every Slack thread references a ticket, every log entry correlates with a commit, every database subscription FKs to a real customer account.
- **Graded agent evaluation** measuring programmatic correctness (did it find the right data?), trajectory efficiency (how many commands, tokens, dollars?), and LLM-judged quality (is the output actually useful?) — all in a single composite score.
- **MCP server** exposing any scenario as a standard Model Context Protocol endpoint, so Claude, Cursor, OpenAI agents, or any MCP client can connect and drive the workspace interactively.
- **Docker mock suite** with fake HTTP backends for all services, a Mirage daemon, and an MCP server — one `docker compose up` to stand up the entire test environment.
- **Enterprise Portal** showing simulated department tools (IT helpdesk, HR, Finance, Engineering, Customer Support, Compliance) with realistic seed data.
- **Agent Console** where users assign cross-department tasks and watch the AI agent work in real-time.

______________________________________________________________________

## 1. Install

```bash
# All commands run from the repo root — never cd into packages/eval
uv sync
cp .env.example .env
```

Edit `.env` (at the repo root) and set your LLM API key. OpenAI or any OpenAI-compatible provider works:

```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5-mini

# Kimi (cheaper for testing)
OPENAI_API_KEY=your-kimi-key
OPENAI_BASE_URL=https://api.moonshot.ai/v1
OPENAI_MODEL=kimi-k2.6
```

## 2. Seed (once per scenario)

```bash
uv run mirage-eval seed --scenario northhill_corp
uv run mirage-eval seed --scenario onboarding_it
```

## 3. Start the Docker stack

**Production (no hot reload):**

```bash
cd docker && docker compose up --build
# → http://localhost:8080
```

**Development (hot reload):** see the root [README](../../README.md#development-with-hot-reload). Quick version:

```bash
# Terminal 1
cd docker && docker compose -f docker-compose.services.yml up --build

# Terminal 2 (repo root)
RELOAD=1 uv run python frontends/platform/server.py

# Terminal 3
cd frontends/platform && npm install && npm run dev
# → http://localhost:5173
```

| Service          | Port | What it does                                               |
| ---------------- | ---- | ---------------------------------------------------------- |
| arcadia-platform | 8080 | Unified UI (production compose only)                       |
| platform-ui      | 5173 | Vite dev server (dev compose only)                         |
| mock-services    | 3000 | Mock HTTP APIs for Slack, GitHub, Jira, PagerDuty, Datadog |
| mirage           | 8081 | MCP server over Streamable HTTP                            |

Verify the stack is up:

```bash
curl http://localhost:8080/api/health
curl http://localhost:3000/health
```

## 4. Run an agent against the stack

With `.env` configured (all commands from the repo root):

```bash
uv sync                       # must run after pulling new changes

# Against Docker MCP server (HTTP, port 8081 — Docker must be running)
uv run python vendor/mirage/examples/python/mcp/mcp_agent_demo.py --mode docker

# Against local MCP server (stdio, no Docker needed)
uv run python vendor/mirage/examples/python/mcp/mcp_agent_demo.py --mode local
```

The agent connects via MCP, discovers the `execute` tool, and uses shell commands (`ls`, `cat`, `jq`, `grep`) to investigate the NorthHill Corp enterprise data across all services.

## 5. Connect from Cursor or Claude Desktop

Add to your MCP config:

```json
{
  "mcpServers": {
    "mirage": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/arcadia/packages/eval", "mirage-mcp", "--scenario", "northhill_corp"]
    }
  }
}
```

Or connect to the Docker MCP server at `http://localhost:8081/mcp`.

## 6. Run evals

```bash
# Single task
uv run mirage-eval run \
  --scenario northhill_corp \
  --task enterprise_review \
  --model gpt-5-mini --seed 1

# Full sweep
uv run mirage-eval sweep \
  --scenario northhill_corp \
  --models gpt-5-mini --seeds 1 --yes
```

Results: `results/<scenario>/<sweep_id>/SUMMARY.md`

### Scorecard indexing

Scorecards and sweep aggregates are always written to JSON files under
`results/<scenario>/<sweep_id>/` (the portable source of truth). When `DATABASE_URL`
is set, the harness *also* writes each scorecard and the sweep aggregate through to the
shared store (the `scorecards` / `sweep_aggregates` tables in `arcadia_store`), so the
platform's results API can serve them DB-first across machines. With `DATABASE_URL`
unset, indexing is a silent no-op and only the JSON files are produced.

```bash
DATABASE_URL=postgresql+asyncpg://arcadia:arcadia@localhost:5432/arcadia \
  uv run mirage-eval sweep --scenario northhill_corp --models gpt-5-mini --seeds 1 --yes
```

### Available tasks (northhill_corp)

| Task                        | Mounts exercised                                                   | What the agent must do                                                                      |
| --------------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------- |
| `enterprise_review`         | All 13                                                             | Cross-department review covering IT, HR, Finance, Engineering, Customer Support, Compliance |
| `customer_revenue_analysis` | `/database`, `/customers`                                          | Cross-reference subscriptions with CRM accounts to identify revenue risk                    |
| `incident_forensics`        | `/pagerduty`, `/datadog`, `/github`, `/s3`, `/customers`, `/slack` | Deep forensic investigation of INC-5521 across logs, metrics, code, and customer impact     |

## 7. Run tests

```bash
# Backend (Python) — all eval + scenario tests (128 tests)
cd packages/eval && uv run pytest

# Framework tests only (fixture resources, workspace integration, seed, ticketing)
cd packages/eval && uv run pytest tests/ -v

# NorthHill Corp scenario tests only (seed, workspace, portal data, platform server)
cd packages/eval && uv run pytest scenarios/northhill_corp/tests/ -v

# Frontend (TypeScript) — from repo root
cd frontends/platform && npm run test:run
```

### Test coverage

**Framework tests** (`tests/`):

| Suite                              | Tests | What it covers                                                                               |
| ---------------------------------- | ----- | -------------------------------------------------------------------------------------------- |
| `test_northhill_scenario.py`       | 11    | Manifest loading, task listing, rubric weights, oracle coverage, builder/seeder resolution    |
| `test_fixture_resources.py`        | 40    | All 13 Fake*Resources: instantiation, schema validation, data completeness per mount         |
| `test_workspace_integration.py`    | 23    | Full workspace: ls/cat/jq across all 13 mounts, cross-mount data referencing, RAM writes     |
| `test_seed_generation.py`          | 27    | Seed completeness, volume checks, cross-reference integrity, deterministic output            |
| `test_ticketing_commands.py`       | 14    | Helpdesk write commands: create, comment, transition, assign, priority, full lifecycle       |
| `test_scorers_units.py`            | 9     | Programmatic gates, trajectory budget, composite scoring, failure mode tagging               |
| `test_runner_smoke.py`             | 1     | Runner captures artifacts even when agent fails (no LLM)                                     |
| `test_scenario_manifest.py`        | 3     | onboarding_it manifest loading, task listing, YAML validation                                |

**Scenario tests** (`scenarios/northhill_corp/tests/`):

| Suite                                 | Tests | What it covers                                                                               |
| ------------------------------------- | ----- | -------------------------------------------------------------------------------------------- |
| `test_seed_completeness.py`           | 31    | All mounts seeded, generated entities, cross-references, JSON validity, idempotency          |
| `test_end_to_end.py`                  | 18    | Full workspace: mount discovery, database/S3 reads, cross-system correlation, agent workflow |
| `test_docker_deployment.py`           | 18    | Dockerfile structure, compose services, seeded data compatibility, file format validation    |
| `test_portal_data_serving.py`         | 20    | Portal disk-reading patterns, env var config, Docker wiring                                  |
| `test_platform_server_integration.py` | 32    | FastAPI server: health, sessions, workspace execution, all portal endpoints, disk fallback   |
| `test_workspace_integration.py`       | 11    | Full Mirage workspace: ls, cat, find across all 13 mounts                                    |
| `test_mock_server_data.py`            | 12    | Mock server data loading, status values, cross-reference integrity                           |

**Frontend tests** (`frontends/platform/`):

| Suite             | Tests | What it covers                                             |
| ----------------- | ----- | ---------------------------------------------------------- |
| Frontend (Vitest) | 106   | API client, SSE hook, all 16 React components, App integration |

## Scenarios

| Scenario         | Domain                          | Services                                                                                      |
| ---------------- | ------------------------------- | --------------------------------------------------------------------------------------------- |
| `northhill_corp` | Full enterprise (6 departments) | Slack, Sheets, Docs, ITSM, GitHub, PagerDuty, Datadog, Finance, CRM, Compliance, Database, S3 |
| `onboarding_it`  | HR onboarding + IT helpdesk     | Slack, GSheets, GDocs, ITSM                                                                   |
| `bi_analytics`   | (placeholder)                   | ---                                                                                           |

## Adding a scenario

```bash
uv run mirage-eval scenario new my_scenario
# Edit scenarios/my_scenario/seed.py, mounts.py, tasks/*.yaml
uv run mirage-eval seed --scenario my_scenario
uv run mirage-eval run --scenario my_scenario --task <id>
```

______________________________________________________________________

## Arcadia Platform UI

The unified platform at http://localhost:8080 (Docker) combines three sections:

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

For local dev:

```bash
uv run python frontends/platform/server.py                    # backend on :8080
cd frontends/platform && npm install && npm run dev            # frontend on :5173
```
