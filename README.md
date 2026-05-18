# Arcadia

**The governed data access layer for autonomous agents.**

Arcadia bridges the gap between sandbox isolation (which solves security) and enterprise data systems (which contain the information agents need). It projects catalog, governance, and lineage capabilities directly into the agent's execution boundary through a virtual filesystem interface that requires zero new SDKs.

## Architecture

```
Agent (any framework, any language)
  → Virtual Filesystem (/workspace/)
    → Catalog Proxy (Iceberg, Snowflake, MCP, PostgreSQL, S3)
      → Policy Engine (column ACL, row filters, budget enforcement)
      → Credential Broker (short-lived tokens via virtio-vsock)
      → Lineage Emitter (OpenLineage events for every access)
    → Enterprise data (governed, audited, discoverable)
```

## Components

| Package | Description |
|---------|-------------|
| `packages/eval` | Scenario-driven eval harness for testing agents on cross-domain enterprise tasks |
| `packages/catalog-proxy` | Translation layer between the VFS and external data sources |
| `packages/credential-broker` | Host-side credential broker for secure token injection |
| `packages/lineage` | Lineage emitter producing OpenLineage-compatible audit events |
| `packages/policy` | Governance engine: column-level ACL, row filters, compute budgets |
| `packages/workspace-vfs` | VFS extensions: dot-file metadata convention, query.json handler |

## Quick Start

```bash
# Install all packages
uv sync

# Seed a scenario
cd packages/eval
uv run mirage-eval seed --scenario meridian_labs

# Run an eval
uv run mirage-eval run \
  --scenario meridian_labs \
  --task incident_investigation \
  --model gpt-5-mini --seed 1

# Or start the full Docker stack
cd docker
docker compose up --build
```

## Upstream Mirage

Arcadia vendors [mirage](https://github.com/strukto-ai/mirage) under `vendor/mirage/` via git subtree. To sync:

```bash
git subtree pull --prefix=vendor/mirage upstream main --squash
```
