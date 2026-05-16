# enterprise/ — Mirage Evaluation Harness

## 1. Install

```bash
cd enterprise
uv sync
cp .env.example .env          # set OPENAI_API_KEY=sk-...
```

## 2. Seed (once per scenario)

```bash
uv run mirage-eval seed --scenario onboarding_it
uv run mirage-eval seed --scenario meridian_labs
```

## 3. Start the Docker stack (recommended)

Runs mock backend services (Slack, GitHub, Jira, PagerDuty, Datadog), the Mirage HTTP daemon, and the MCP server — all in one command.

```bash
cd docker
docker compose up --build
```

| Service | Port | What it does |
|---|---|---|
| mock-services | 3000 | Mock HTTP APIs for Slack, GitHub, Jira, PagerDuty, Datadog |
| mirage-api | 8080 | Mirage HTTP daemon (workspace CRUD, execute, sessions) |
| mirage-mcp | 8081 | MCP server over Streamable HTTP |

Verify the stack is up:

```bash
curl http://localhost:3000/health
curl http://localhost:3000/slack/api/conversations.list
curl http://localhost:3000/pagerduty/incidents
curl http://localhost:3000/github/repos/meridian-labs/payments-api/deployments
curl 'http://localhost:3000/jira/rest/api/2/search?jql=project=OPS'
curl -X POST http://localhost:3000/datadog/api/v1/logs/search \
  -H 'Content-Type: application/json' \
  -d '{"filter":{"query":"connection pool"}}'
```

## 4. Run an agent against the stack

With Docker running and `OPENAI_API_KEY` set:

```bash
# Against Docker MCP server (HTTP, port 8081)
./python/.venv/bin/python examples/python/mcp/mcp_agent_demo.py --mode docker

# Against local MCP server (stdio, no Docker needed)
./python/.venv/bin/python examples/python/mcp/mcp_agent_demo.py --mode local
```

The agent connects via MCP, discovers the `execute` tool, and uses shell commands (`ls`, `cat`, `jq`, `grep`) to investigate the Meridian Labs incident across all 5 services.

## 5. Connect from Cursor or Claude Desktop

Add to your MCP config:

```json
{
  "mcpServers": {
    "mirage": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/enterprise", "mirage-mcp", "--scenario", "meridian_labs"]
    }
  }
}
```

Or connect to the Docker MCP server at `http://localhost:8081/mcp`.

## 6. Run evals

```bash
# Single task
uv run mirage-eval run \
  --scenario meridian_labs \
  --task incident_investigation \
  --model gpt-5-mini --seed 1

# Full sweep
uv run mirage-eval sweep \
  --scenario meridian_labs \
  --models gpt-5-mini --seeds 1 --yes
```

Results: `results/<scenario>/<sweep_id>/SUMMARY.md`

## 7. Run tests

```bash
uv run pytest
```

## Scenarios

| Scenario | Domain | Services |
|---|---|---|
| `onboarding_it` | HR onboarding + IT helpdesk | Slack, GSheets, GDocs, ITSM |
| `meridian_labs` | SRE incident response | Slack, Jira, GitHub, PagerDuty, Datadog |

## Adding a scenario

```bash
uv run mirage-eval scenario new my_scenario
# Edit scenarios/my_scenario/seed.py, mounts.py, tasks/*.yaml
uv run mirage-eval seed --scenario my_scenario
uv run mirage-eval run --scenario my_scenario --task <id>
```

## Layout

```
enterprise/
  mirage_eval/          # framework: CLI, runner, scorers, report, MCP server
  scenarios/            # per-scenario seed data, mounts, tasks, tests
  docker/               # Dockerfile, docker-compose, mock backend server
  results/              # sweep outputs (gitignored)
  tests/                # framework-level tests
```
