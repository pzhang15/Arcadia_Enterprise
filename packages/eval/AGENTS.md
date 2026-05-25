# Agent Overview — Eval Package Structure and Architecture

This document is for AI agents working on the eval harness. For human quickstart, see [README.md](README.md).

This package lives at `packages/eval/` within the Arcadia platform repo.

## Package Structure

```
packages/eval/
│
├── pyproject.toml                  # Package config, dependencies, CLI entry points
├── uv.lock                        # Lockfile for reproducible installs
├── README.md                      # Human-facing quickstart and usage guide
├── AGENTS.md                      # This file — agent-facing project overview
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
│   │   ├── fake_finance.py        #   Finance: expenses, POs, invoices, budgets
│   │   ├── fake_customers.py      #   CRM: customer accounts, escalations
│   │   ├── fake_compliance.py     #   Legal: contracts, audits, policies
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
│   ├── northhill_corp/             # Full enterprise (6 departments, 28 employees, 143 files)
│   │   ├── scenario.yaml          #   Manifest (id, builders, paths)
│   │   ├── seed.py                #   Generates all department data
│   │   ├── mounts.py              #   build_l1_workspace (11 mounts)
│   │   ├── personas.yaml          #   28 employees across 8 teams
│   │   ├── tasks/
│   │   │   └── enterprise_review.yaml
│   │   ├── tests/
│   │   └── fixture/               #   Seed output (gitignored)
│   │
│   ├── onboarding_it/             # NorthHill Corp HR + IT helpdesk
│   │   ├── scenario.yaml
│   │   ├── seed.py                #   Generates Slack/Sheets/Docs/Tickets corpus
│   │   ├── mounts.py              #   build_l1_workspace (6 mounts)
│   │   ├── seed_real.py           #   L2: push corpus to real Slack + Google
│   │   ├── personas.yaml          #   7 employees, 3 teams
│   │   ├── tasks/
│   │   │   ├── onboarding_status.yaml
│   │   │   ├── provision_new_hire.yaml
│   │   │   ├── ticket_triage.yaml
│   │   │   ├── incident_followup.yaml
│   │   │   └── adversarial/       #   Adversarial variants
│   │   ├── tests/
│   │   └── fixture/
│   │
│   ├── bi_analytics/              # BI analytics (placeholder)
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
│   └── bi_analytics/              # Placeholder, not yet implemented
│
├── docker/                        # ── Docker testing suite ──
│   ├── Dockerfile                 #   Python 3.12 + uv, seeds all scenarios at build time
│   ├── docker-compose.yml         #   6 services (see below)
│   └── mock_server.py             #   Unified FastAPI mock (all services)
│
├── tests/                         # ── Framework-level tests ──
│   ├── test_runner_smoke.py
│   ├── test_scenario_manifest.py
│   └── test_scorers_units.py
│
├── canvases/                      #   Cursor Canvas dashboards (generated by sweeps)
├── scripts/                       #   Eval scripts (run_sweep.sh)
└── results/                       #   Sweep outputs (gitignored)
```

Note: Frontends (observability, portal, console) live at `frontends/` in the repo root.
Docker config lives at `docker/` in the repo root.

## How the pieces connect

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
        → FakeFinanceResource reads /finance/expenses/...
        → FakeCustomersResource reads /customers/accounts/...
        → FakeComplianceResource reads /compliance/audits/...
      → Observer writes JSONL to /.sessions/
    → stdout/stderr returned to agent
  → Agent reasons, calls execute again (loop)
  → Final output scored by programmatic gates + LLM judge
```

## Docker services (in docker/ at repo root)

```
docker/docker-compose.yml defines 6 services:

  observability (:8082)  ← event relay + observability React app (frontends/observability)
       ↑ POST /ingest
  mock-services (:3000)  ← FastAPI mocking Slack/GitHub/Jira/PD/DD/Finance/CRM/Compliance
       ↑ depends_on
  mirage-api    (:8080)  ← Mirage HTTP daemon (workspace CRUD + execute)
  mirage-mcp    (:8081)  ← MCP server over streamable-http
  portal        (:8083)  ← Enterprise portal (frontends/portal, reads northhill_corp fixture)
  console       (:8084)  ← Agent console (frontends/console, session manager + agent runner)
```

## Data flow: real-time observability

```
MCP Server execute()
  → POST event to Relay (:8082/ingest)
    → Relay buffers in deque(maxlen=5000)
    → Fan-out to SSE subscribers via asyncio.Queue

Mock Server middleware
  → POST event to Relay (:8082/ingest)

Browser (Observability UI or Agent Console)
  → EventSource("/events")
    → SSE stream from Relay
    → React components render in real-time
```

## Key data shapes

### OpRecord (python/mirage/observe/record.py)

Fields: op, path, source, bytes, timestamp, duration_ms, mount_prefix, fingerprint, revision

### LogEntry (python/mirage/observe/log_entry.py)

Two types:

- `type="op"`: agent, session, timestamp, op, path, source, bytes, duration_ms
- `type="command"`: agent, session, timestamp, command, exit_code, stdout (truncated 4096)

### ExecutionRecord (python/mirage/workspace/types.py)

Fields: agent, command, stdout, stdin, exit_code, tree (ExecutionNode), timestamp, session_id

### ScoreCard (enterprise/mirage_eval/scorers/composite.py)

Fields: scenario_id, task_id, surface, model, seed, sweep_id, passed_gates, programmatic, trajectory, judge, composite, failure_modes, error

### Event types emitted to relay

- `mcp_tool_call`: tool, arguments, result, result_bytes, duration_ms, error
- `command`: agent, session, command, exit_code, stdout
- `op`: agent, session, op, path, source, bytes, duration_ms, mount_prefix
- `mock_request`: service, method, path, query, status_code, response_bytes, duration_ms
- `agent_status`: status (running/completed), task, result (console only)

## Scenario seed pattern

Each scenario has a `seed.py` with a `main(root, *, clean=True) -> Path` function that:

1. Creates the `fixture/disk/` directory tree
1. Writes JSON files organized by service mount (slack/, tickets/, sheets/, etc.)
1. Returns the root path

The `scenario.yaml` references the seed function via `fixture.seed: scenarios.<name>.seed:main`.

The `mounts.py` creates a Workspace with mounts pointing at the seed output. Each mount maps a virtual path prefix to a FakeResource (DiskResource subclass with a PROMPT constant).

## Fixture resource pattern

All fake resources extend `mirage.resource.disk.DiskResource`:

- Define a `PROMPT` class variable describing the filesystem layout
- Optionally define `WRITE_PROMPT` and register `@command` functions for mutation
- Constructor takes `root: Path` and passes to `super().__init__(root)`

To add a new service:

1. Create `enterprise/mirage_eval/fixtures/fake_<service>.py` with `Fake<Service>Resource(DiskResource)`
1. Add to `fixtures/__init__.py`
1. Add seed data generation to the scenario's `seed.py`
1. Add mount in the scenario's `mounts.py`
1. Optionally add mock HTTP endpoints in `docker/mock_server.py`

## northhill_corp scenario: cross-reference map

```
INC-5521 (PagerDuty triggered)
  ↔ OPS-1247 (ticket, linked_incidents)
  ↔ deployment d4e5f6 (GitHub)
  ↔ commit f3a1b2c8 (connection pool 50→10)
  ↔ CS-1001 (customer ticket, login failures caused by incident)
  ↔ ESC-1001 (customer escalation)
  ↔ GlobalTech ACCT-1001 (health_score: 45, at risk)

Alex Rivera (new hire)
  ↔ INC-1001 (laptop), INC-1002 (AWS), INC-1003 (Okta), INC-1004 (GitHub)
  ↔ New Hire Tracker SH101 row
  ↔ Slack #onboarding, DMs with Diana/Sam/Marcus

EXP-1003 (expense) ↔ PO-1002 (purchase order, same vendor)
LGL-1002 (ticket) ↔ AUDIT-2026-SOC2 (audit)
AUDIT-2026-SOC2 checklist ↔ POL-1001, POL-1002, POL-1003 (policies)
```
