# Arcadia Eval — Governed AI Workspaces for Heterogeneous Enterprise Environments

This is the `packages/eval` component of the [Arcadia](../../README.md) platform.

It simulates realistic enterprise environments where AI agents navigate cross-domain data under workspace-level governance — the same filesystem abstraction, the same observation pipeline, and the same scoring framework that would run in production, but backed by synthetic seed data so you can iterate without credentials, without cost, and without risk.

What you get:

- **Simulated enterprise scenarios** with coherent, cross-referenced data across 5+ services (Slack, Jira, GitHub, PagerDuty, Datadog, GSheets, GDocs, ITSM). Every ticket references a deployment, every Slack thread references a ticket, every log entry correlates with a commit.
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

## 3. Start the Docker stack (recommended)

Runs all services — mock backends, Mirage daemon, MCP server, portal, console, and observability — in one command.

```bash
cd docker && docker compose up --build
```

| Service       | Port | What it does                                               |
| ------------- | ---- | ---------------------------------------------------------- |
| observability | 8082 | Observability UI + event relay (SSE + results API)         |
| portal        | 8083 | Enterprise department portal (6 departments)               |
| console       | 8084 | Agent console (interactive AI agent workspace)             |
| mock-services | 3000 | Mock HTTP APIs for Slack, GitHub, Jira, PagerDuty, Datadog |
| mirage-api    | 8080 | Mirage HTTP daemon (workspace CRUD, execute, sessions)     |
| mirage-mcp    | 8081 | MCP server over Streamable HTTP                            |

Verify the stack is up:

```bash
curl http://localhost:3000/health
curl http://localhost:8082/api/health
curl http://localhost:8083/api/health
curl http://localhost:8084/api/health
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

## 7. Run tests

```bash
uv run pytest
```

## Scenarios

| Scenario        | Domain                          | Services                                                                        |
| --------------- | ------------------------------- | ------------------------------------------------------------------------------- |
| `northhill_corp` | Full enterprise (6 departments) | Slack, Sheets, Docs, ITSM, GitHub, PagerDuty, Datadog, Finance, CRM, Compliance |
| `onboarding_it`  | HR onboarding + IT helpdesk     | Slack, GSheets, GDocs, ITSM                                                     |
| `bi_analytics`   | (placeholder)                   | ---                                                                             |

## Adding a scenario

```bash
uv run mirage-eval scenario new my_scenario
# Edit scenarios/my_scenario/seed.py, mounts.py, tasks/*.yaml
uv run mirage-eval seed --scenario my_scenario
uv run mirage-eval run --scenario my_scenario --task <id>
```

______________________________________________________________________

## Apps

### Observability UI

Real-time observability dashboard for agent sessions. Shows every command the agent runs, every resource it touches, and how it scores.

| View             | What it shows                                                                         |
| ---------------- | ------------------------------------------------------------------------------------- |
| Command Timeline | Live stream of every `execute()` call — command, exit code, timing, stdout, mount I/O |
| MCP Traffic      | JSON-RPC request/response pairs for the MCP protocol layer                            |
| Request Log      | HTTP requests hitting the mock backend services, filterable by service                |
| Resource Map     | Which mounts the agent touched, read/write counts, bytes transferred                  |
| Scorecard        | Eval results — composite scores, gate pass/fail, judge rubric, failure modes          |

Open http://localhost:8082 (Docker) or run in dev mode:

```bash
cd frontends/observability && pip install fastapi uvicorn httpx && python server.py
cd frontends/observability && npm install && npm run dev   # http://localhost:5173
```

### Enterprise Portal

Simulates the enterprise tools employees use daily — ServiceNow, Workday, Zendesk, etc. — organized by department.

| Department       | What it shows                                                   |
| ---------------- | --------------------------------------------------------------- |
| IT Helpdesk      | Ticket queue (ServiceNow-style), filterable by status/priority  |
| HR & People      | Employee directory, onboarding tracker, PTO calendar            |
| Finance          | Expense report queue, purchase orders, department budgets       |
| Engineering      | Active incidents, deployment log, monitoring alerts             |
| Customer Support | Support tickets (Zendesk-style), account health cards           |
| Compliance       | Contract review queue, audit checklists, policy acknowledgments |

Open http://localhost:8083 (Docker) or run in dev mode:

```bash
cd frontends/portal && pip install fastapi uvicorn httpx && python server.py
cd frontends/portal && npm install && npm run dev   # http://localhost:5174
```

### Agent Console

The interactive AI agent workspace. Users select which department services to connect, describe a task in natural language, and watch the agent work across services in real-time.

1. **Service Connector** — toggle which departments the agent can access
1. **Task Dialog** — type a task or use quick-action presets
1. **Live Execution** — watch the agent run commands in real-time via SSE
1. **Results Summary** — see what the agent accomplished: services touched, files created, structured report

Open http://localhost:8084 (Docker) or run in dev mode:

```bash
cd frontends/console && pip install fastapi uvicorn httpx && python server.py
cd frontends/console && npm install && npm run dev   # http://localhost:5175
```
