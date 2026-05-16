# enterprise/ — Mirage Evaluation Harness

Scenario-driven eval for Mirage agents. Measures programmatic gates, trajectory metrics, and LLM-as-judge quality across cross-domain enterprise tasks.

## Setup

```bash
cd enterprise
uv sync
cp .env.example .env          # set OPENAI_API_KEY=sk-...
```

## Run an eval

```bash
# Seed the corpus (once per scenario)
uv run mirage-eval seed --scenario onboarding_it

# Run a single task
uv run mirage-eval run \
  --scenario onboarding_it \
  --task onboarding_status \
  --model gpt-5-mini --seed 1

# Run a full sweep (all tasks x models x seeds)
uv run mirage-eval sweep \
  --scenario onboarding_it \
  --models gpt-5-mini,gpt-5 --seeds 1,2,3 --yes
```

Results land in `results/<scenario>/<sweep_id>/` with `scorecard.json`, `SUMMARY.md`, and a Cursor canvas dashboard.

## Run tests

```bash
uv run pytest
```

## MCP server

Expose any scenario as an MCP server so Claude Desktop, Cursor, or any MCP client can interact with the simulated data.

```bash
# stdio (local agent / Cursor / Claude Desktop)
uv run mirage-mcp --scenario meridian_labs

# HTTP (Docker / remote)
uv run mirage-mcp --scenario meridian_labs --transport streamable-http
```

Cursor/Claude Desktop config (`mcp.json`):

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

## Docker mock suite

Run mock backend services (Slack, GitHub, Jira, PagerDuty, Datadog) + Mirage daemon + MCP server:

```bash
cd docker
docker compose up --build
```

| Service | Port | Purpose |
|---|---|---|
| mock-services | 3000 | Mock APIs for all 5 backends |
| mirage-api | 8080 | Mirage HTTP daemon (workspace CRUD + execute) |
| mirage-mcp | 8081 | MCP server (Streamable HTTP) |

## Scenarios

| Scenario | Domain | Services |
|---|---|---|
| `onboarding_it` | HR onboarding + IT helpdesk | Slack, GSheets, GDocs, ITSM |
| `meridian_labs` | SRE incident response | Slack, Jira, GitHub, PagerDuty, Datadog |

## Layout

```
enterprise/
  mirage_eval/          # framework: CLI, runner, scorers, report, MCP server
  scenarios/            # per-scenario seed data, mounts, tasks, tests
  docker/               # Dockerfile, docker-compose, mock backend server
  results/              # sweep outputs (gitignored)
  tests/                # framework-level tests
```

## Adding a scenario

```bash
uv run mirage-eval scenario new my_scenario
# Edit scenarios/my_scenario/seed.py, mounts.py, tasks/*.yaml
uv run mirage-eval seed --scenario my_scenario
uv run mirage-eval run --scenario my_scenario --task <id>
```
