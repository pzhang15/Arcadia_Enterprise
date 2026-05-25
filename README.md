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
├── frontends/                # React apps
│   ├── observability/        # Real-time agent monitoring dashboard
│   ├── portal/               # Simulated enterprise department tools
│   └── console/              # Interactive agent task runner
├── vendor/mirage/            # Upstream mirage VFS (git subtree)
├── docker/                   # Docker compose for the full stack
└── pyproject.toml            # Workspace root
```

## Quick start

```bash
# All commands run from the repo root
uv sync

# Seed and run an eval scenario
uv run mirage-eval seed --scenario northhill_corp
uv run mirage-eval run --scenario northhill_corp --task enterprise_review --model gpt-5-mini --seed 1

# Run tests
uv run pytest

# Or start everything in Docker
cd docker && docker compose up --build
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
