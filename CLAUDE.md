# CLAUDE.md

Arcadia is the governed data access layer for autonomous agents. It provides governed, discoverable, and lineage-tracked data access to AI agents operating inside sandboxed execution environments, using a virtual filesystem interface that requires zero new SDKs.

## Repo Layout

```
arcadia/
├── vendor/mirage/          # Upstream mirage (git subtree from strukto-ai/mirage)
│   ├── python/             # mirage-ai Python package
│   ├── typescript/         # mirage TS monorepo
│   ├── docs/               # mirage documentation
│   └── examples/           # mirage examples
├── packages/               # Arcadia components (uv workspace members)
│   ├── eval/               # Eval harness (mirage_eval, scenarios, tests)
│   ├── catalog-proxy/      # Catalog Proxy (Iceberg, Snowflake, MCP adapters)
│   ├── credential-broker/  # Credential Broker (virtio-vsock token injection)
│   ├── lineage/            # Lineage Emitter (OpenLineage events)
│   ├── policy/             # Policy Engine (column ACL, row filters, budgets)
│   └── workspace-vfs/      # VFS extensions (dot-file metadata, query.json)
├── frontends/              # React apps
│   ├── observability/      # Observability UI (:8082)
│   ├── portal/             # Enterprise Portal (:8083)
│   └── console/            # Agent Console (:8084)
├── docker/                 # Docker compose + Dockerfile
├── pyproject.toml          # uv workspace root
└── .pre-commit-config.yaml
```

Run Python commands from the repo root. The uv workspace resolves all packages.

## Development Setup

This project uses `uv` for Python dependency management. Install dependencies with:

```bash
uv sync
```

To work on a specific package:

```bash
cd packages/eval && uv sync
```

### Syncing upstream mirage

The `vendor/mirage/` directory is a git subtree of `strukto-ai/mirage`. To pull latest upstream:

```bash
git subtree pull --prefix=vendor/mirage upstream main --squash
```

### Running examples

Examples live in `vendor/mirage/examples/`. To run them from the repo root:

```bash
./vendor/mirage/python/.venv/bin/python vendor/mirage/examples/python/s3/s3.py
```

## Backward Compatibility

- No need to consider backward compatibility for the code.

## Create a PR

When asked to create a PR, follow these steps:

1. Run `./vendor/mirage/python/.venv/bin/pre-commit run --all-files` from the repo root.
1. Run `cd packages/eval && uv run pytest` to run the eval tests.
1. Run `git add -A` to add all changes.
1. Run `git checkout -b <branch-name>` to create a new branch.
1. Run `git commit -m "<commit-message>"` to commit the changes.
1. Run `git push origin <branch-name>` to push.
1. Run `gh pr create --title "<pr-title>" --body "<pr-body>"` to create a PR.

## Commands

### Linting and Formatting

```bash
./vendor/mirage/python/.venv/bin/pre-commit run --all-files
```

## Type Conventions

- Paths must always be represented as `PathSpec`, never raw strings. All functions that accept or return paths use `list[str | PathSpec]` where `str` is for text arguments and `PathSpec` is for paths. Never pass a path as a plain `str` — wrap it in `PathSpec`.

## Rules

- Avoid add any comments or docstrings on the top of the file.
- Do not create nested functions.
- Add type to Args for docstring.
- Do not add comment after each line of code in the format of "# 10MB - trigger segmentation for files larger than this". The most you can add is "# 10MB".
- For all imports you need to put to the top of the file. Don't have imports within each function.
- **No circular imports.**
- **Never silently swallow exceptions.**
- **Never call `asyncio.run()` inside a sync function that might be invoked under an outer event loop.**
- Please don't change any file name unless I ask you to do so.
- Don't add too many printings or comments in the code.
- Don't add README.md unless I ask you to do so.
- When adding features, commands, or configuration, always update the relevant README.md.
- Use uv add to install new dependencies.
