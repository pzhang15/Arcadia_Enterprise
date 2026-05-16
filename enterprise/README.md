# enterprise/ — Mirage Evaluation Harness

## 1. Install

```bash
cd enterprise
uv sync
cp .env.example .env
```

Edit `.env` and set your LLM API key. OpenAI or any OpenAI-compatible provider works:

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

With `.env` configured:

```bash
cd enterprise
uv sync                       # must run after pulling new changes

# Against Docker MCP server (HTTP, port 8081 — Docker must be running)
uv run python ../examples/python/mcp/mcp_agent_demo.py --mode docker

# Against local MCP server (stdio, no Docker needed)
uv run python ../examples/python/mcp/mcp_agent_demo.py --mode local
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
| `bi_analytics` | (placeholder) | — |

## Adding a scenario

```bash
uv run mirage-eval scenario new my_scenario
# Edit scenarios/my_scenario/seed.py, mounts.py, tasks/*.yaml
uv run mirage-eval seed --scenario my_scenario
uv run mirage-eval run --scenario my_scenario --task <id>
```

## Observability UI (planned)

See `app/HANDOFF.md` for a comprehensive spec covering 5 views: live command timeline, resource access map, MCP traffic inspector, mock backend request log, and eval scorecard dashboard.

---

## Repo Structure

```
enterprise/
│
├── pyproject.toml                  # Package config, dependencies, CLI entry points
├── uv.lock                        # Lockfile for reproducible installs
├── .env.example                   # Template for API keys (copy to .env)
├── .gitignore                     # Ignores results/, fixtures, pycache
├── README.md                      # This file
│
├── mirage_eval/                   # ── Framework (scenario-agnostic) ──
│   ├── cli.py                     # CLI: seed, run, sweep, report, mcp-serve, scenario new
│   ├── mcp_server.py              # MCP server (stdio + HTTP) wrapping any workspace
│   ├── config.py                  # TaskConfig, TrajectoryBudget, JudgeConfig (pydantic)
│   ├── scenario.py                # ScenarioManifest loader + ENTERPRISE_ROOT
│   │
│   ├── fixtures/                  # Fake resources (DiskResource + PROMPT wrappers)
│   │   ├── fake_slack.py          #   Slack (reuses mirage's real Slack PROMPT)
│   │   ├── fake_gdocs.py          #   Google Docs
│   │   ├── fake_gsheets.py        #   Google Sheets
│   │   ├── fake_ticketing.py      #   ITSM tickets (+ helpdesk-* write commands)
│   │   ├── fake_github.py         #   GitHub deployments/commits/PRs
│   │   ├── fake_pagerduty.py      #   PagerDuty incidents/services
│   │   ├── fake_datadog.py        #   Datadog logs/metrics
│   │   └── build_snapshot.py      #   Workspace → tar snapshot utility
│   │
│   ├── runner/                    # Agent execution engine
│   │   ├── common.py              #   run_one_task(), RunArtifacts, TokenUsage
│   │   ├── l1_synthetic.py        #   L1 runner (offline, fake resources)
│   │   └── l2_real.py             #   L2 runner (real Slack/GitHub/Google APIs)
│   │
│   ├── scorers/                   # Scoring pipeline
│   │   ├── composite.py           #   ScoreCard, score_run() (blends all scores)
│   │   ├── programmatic.py        #   Gate checks (files exist, must contain, etc.)
│   │   ├── trajectory.py          #   Trajectory metrics (turns, ops, cost, budget)
│   │   └── llm_judge.py           #   LLM-as-judge (rubric-based quality scoring)
│   │
│   └── report/                    # Output generation
│       ├── aggregate.py           #   AggregateReport from sweep scorecards
│       ├── markdown.py            #   SUMMARY.md writer
│       └── canvas.py              #   Cursor Canvas dashboard (.canvas.tsx)
│
├── scenarios/                     # ── Per-scenario data + tasks ──
│   │
│   ├── onboarding_it/             # Scenario 1: ACME Corp HR + IT helpdesk
│   │   ├── scenario.yaml          #   Manifest (id, builders, paths)
│   │   ├── seed.py                #   Generates Slack/Sheets/Docs/Tickets corpus
│   │   ├── mounts.py              #   build_l1_workspace (6 mounts)
│   │   ├── seed_real.py           #   L2: push corpus to real Slack + Google
│   │   ├── personas.yaml          #   Cast of characters
│   │   ├── tasks/                 #   Task YAMLs (prompt + oracles + judge rubric)
│   │   │   ├── onboarding_status.yaml
│   │   │   ├── provision_new_hire.yaml
│   │   │   ├── ticket_triage.yaml
│   │   │   ├── incident_followup.yaml
│   │   │   └── adversarial/       #   Adversarial variants (missing data, contradictions)
│   │   ├── tests/                 #   Corpus integrity tests
│   │   └── fixture/               #   Seed output + snapshot tar (gitignored)
│   │
│   ├── meridian_labs/             # Scenario 2: Meridian Labs SRE incident response
│   │   ├── scenario.yaml
│   │   ├── seed.py                #   Generates Slack/Tickets/GitHub/PagerDuty/Datadog
│   │   ├── mounts.py              #   build_l1_workspace (6 mounts)
│   │   ├── mounts_docker.py       #   Docker workspace (real resources → mock URLs)
│   │   ├── tasks/
│   │   │   ├── incident_investigation.yaml
│   │   │   └── cross_reference_summary.yaml
│   │   ├── tests/
│   │   └── fixture/
│   │
│   └── bi_analytics/              # Scenario 3: (placeholder, not yet implemented)
│
├── docker/                        # ── Docker testing suite ──
│   ├── Dockerfile                 #   Python 3.12 + uv, seeds data at build time
│   ├── docker-compose.yml         #   3 services: mock-services, mirage-api, mirage-mcp
│   └── mock_server.py             #   Unified FastAPI mock (Slack/GitHub/Jira/PD/DD)
│
├── app/                           # ── Observability UI (planned) ──
│   └── HANDOFF.md                 #   Spec for building the frontend
│
├── tests/                         # ── Framework-level tests ──
│   ├── test_runner_smoke.py       #   Runner completes even when agent fails
│   ├── test_scenario_manifest.py  #   Manifest loads, tasks validate
│   └── test_scorers_units.py      #   Scorer unit tests (gates, trajectory, composite)
│
├── scripts/
│   └── run_sweep.sh               #   Convenience wrapper for sweep command
│
├── canvases/                      #   Cursor Canvas dashboards (generated by sweeps)
└── results/                       #   Sweep outputs: scorecards, artifacts (gitignored)
```

### How the pieces connect

```
Agent (OpenAI/Kimi)
  → MCP Server (mirage_eval/mcp_server.py)
    → Workspace.execute(command)
      → Ops dispatcher routes to mounted resources
        → FakeSlackResource reads /slack/channels/...
        → FakeTicketingResource reads /tickets/queues/...
        → FakeGitHubResource reads /github/repos/...
        → FakePagerDutyResource reads /pagerduty/incidents/...
        → FakeDatadogResource reads /datadog/logs/...
      → Observer writes JSONL to /.sessions/
    → stdout/stderr returned to agent
  → Agent reasons, calls execute again (loop)
  → Final output scored by programmatic gates + LLM judge
```
