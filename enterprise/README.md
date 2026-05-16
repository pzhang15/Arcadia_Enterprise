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

## 3. Choose what to run

### Option A — Run eval (needs OPENAI_API_KEY)

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

### Option B — Run MCP server (interactive testing)

```bash
# stdio (for Cursor / Claude Desktop / CLI agents)
uv run mirage-mcp --scenario meridian_labs

# HTTP (for remote / Docker)
uv run mirage-mcp --scenario meridian_labs --transport streamable-http
```

Connect from Cursor or Claude Desktop (`mcp.json`):

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

### Option C — Run Docker mock suite

```bash
cd docker
docker compose up --build
```

| Service | Port | What it does |
|---|---|---|
| mock-services | 3000 | Fake Slack, GitHub, Jira, PagerDuty, Datadog HTTP APIs |
| mirage-api | 8080 | Mirage HTTP daemon (workspace CRUD + execute) |
| mirage-mcp | 8081 | MCP server over HTTP |

Test the mocks:

```bash
curl http://localhost:3000/health
curl http://localhost:3000/slack/api/conversations.list
curl http://localhost:3000/pagerduty/incidents
curl http://localhost:3000/github/repos/meridian-labs/payments-api/deployments
```

### Option D — Run tests

```bash
uv run pytest
```

## Scenarios

| Scenario | Domain | Mounts |
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
