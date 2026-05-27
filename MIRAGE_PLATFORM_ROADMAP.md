# Mirage Platform Roadmap: From VFS to Agent Runtime Intelligence Layer

> **Audience:** Engineering team, coding agents, and strategic leadership.
> **Purpose:** Defines the feature vision, technical architecture gaps, build-out plan, and implementation guidance for evolving Mirage from a virtual filesystem into a full agent data plane with performance optimization and enterprise governance capabilities.
> **Date:** May 2026

---

## Table of Contents

1. [Strategic Context](#1-strategic-context)
2. [Architecture Overview — Where We Are Today](#2-architecture-overview--where-we-are-today)
3. [Feature Vision: Track 1 — Agent Performance](#3-feature-vision-track-1--agent-performance)
4. [Feature Vision: Track 2 — Governance & Auditability](#4-feature-vision-track-2--governance--auditability)
5. [Technical Gaps & Infrastructure Requirements](#5-technical-gaps--infrastructure-requirements)
6. [Build-Out Plan & Phasing](#6-build-out-plan--phasing)
7. [Implementation Notes for Coding Agents](#7-implementation-notes-for-coding-agents)

---

## 1. Strategic Context

### What Mirage Is Today

Mirage is a **Unified Virtual Filesystem for AI Agents**. It mounts services (S3, Google Drive, Slack, GitHub, Linear, Notion, Postgres, SSH, etc.) behind one filesystem interface. Agents interact with all backends using the same Unix-like tools (`ls`, `cat`, `grep`, `find`, pipes, redirects). The shell is a tree-sitter bash parser + custom executor — no subprocess to `/bin/bash`, no `os.system`.

**Current architecture layers:**

```
Agent / Application
    ↓
Mirage Shell (tree-sitter bash parser + custom executor)
    ↓
Virtual Filesystem (mount tree, path resolution, command dispatch)
    ↓
Dispatcher + Two-Layer Cache (index cache + file cache, RAM or Redis)
    ↓
Resource Backends (S3, Slack, GitHub, Postgres, etc.)
```

### What Mirage Needs to Become

**An agent runtime intelligence layer** — the system that makes agents faster, cheaper, safer, and auditable by controlling the data plane between agents and the world.

Two parallel tracks:

- **Track 1 — Agent Performance:** Make agents that run on Mirage measurably faster, more accurate, and more token-efficient than agents using raw API calls or MCP tools.
- **Track 2 — Governance & Auditability:** Make Mirage the single control plane for enterprise agent data access — audit trails, policy enforcement, PII detection, compliance reporting.

### Why Only Mirage Can Do This

Mirage occupies a unique position in the agent stack: **between the agent's reasoning and the world's data.** The LLM provider sees prompts/completions but not data sources. The agent framework sees tool invocations but doesn't control data flow. Individual services see their own API calls but not cross-service patterns. Mirage sees everything: what data was read, from where, in what order, what was written, and where. This position enables capabilities that are structurally impossible to build from any other layer.

---

## 2. Architecture Overview — Where We Are Today

### Current Codebase Structure (from repo analysis)

```
mirage/
├── python/                     # Python SDK (reference implementation)
│   ├── mirage/
│   │   ├── resource/           # Per-service resource implementations
│   │   │   ├── ram.py
│   │   │   ├── s3.py
│   │   │   ├── slack.py
│   │   │   ├── github.py
│   │   │   ├── linear.py
│   │   │   └── ...             # ~30 resource backends
│   │   ├── agents/             # Agent framework integrations
│   │   │   ├── openai_agents.py
│   │   │   ├── langchain.py
│   │   │   ├── pydantic_ai.py
│   │   │   └── ...
│   │   ├── workspace.py        # Core Workspace class
│   │   └── shell/              # Bash parser + executor
├── typescript/                 # TypeScript SDK
│   ├── packages/
│   │   ├── core/               # Runtime-agnostic primitives
│   │   ├── node/               # Node.js implementation
│   │   ├── browser/            # Browser/edge implementation
│   │   ├── cli/                # CLI binary
│   │   └── agents/             # Agent framework adapters
├── examples/
├── docs/
└── scripts/
```

### Current Capabilities

| Capability | Status | Notes |
|---|---|---|
| Mount tree + path resolution | ✅ Shipped | Core VFS abstraction |
| Bash parser (tree-sitter) | ✅ Shipped | ls, cat, grep, find, head, wc, jq, pipes, redirects, globs |
| Resource backends (~30) | ✅ Shipped | S3, Slack, GitHub, Linear, Postgres, etc. |
| Two-layer cache (index + file) | ✅ Shipped | RAM default, Redis optional |
| Snapshot / clone / replay | ✅ Shipped | Git-style workspace versioning |
| Agent framework integrations | ✅ Shipped | OpenAI Agents, Vercel AI, LangChain, Pydantic AI, CAMEL, OpenHands |
| `ws.file_prompt` system prompt | ✅ Shipped | Static mount description for agent context |
| `mirage provision` dry-run | ✅ Shipped (CLI) | Cost/latency estimation before execution |
| FUSE mount | ✅ Shipped | Host-level filesystem mount for coding agents |
| Custom commands per resource/filetype | ✅ Shipped | `ws.command('cat', { resource: 's3', filetype: 'parquet' }, ...)` |
| Execution traces | ❌ Not built | No structured logging of agent data access |
| Policy engine | ❌ Not built | No write approval, no access controls |
| PII / sensitive data detection | ❌ Not built | No data classification |
| Workspace memory / diffs | ❌ Not built | Cache stores bytes, not agent-relevant state |
| Token-aware formatting | ❌ Not built | Returns raw content regardless of LLM context window |
| Credential management | ❌ Not built | Each resource handles auth independently |
| Dynamic workspace manifests | ❌ Not built | `file_prompt` is static |

---

## 3. Feature Vision: Track 1 — Agent Performance

> **Goal:** Agents running on Mirage complete cross-service tasks faster, more accurately, and using fewer tokens than agents using raw APIs or MCP.

### 3.1 Execution Trace

**What it is:** A structured log of every workspace command — what was read/written, from which mount, timestamps, byte counts, and cache hit/miss status.

**Why it matters:** Foundation for every other feature in both tracks. Performance optimization requires access pattern data. Governance requires audit trails. Both start with the execution trace.

**Data model:**

```typescript
interface TraceEntry {
  trace_id: string;           // Unique per session
  turn_id: string;            // Groups entries within a single agent turn
  timestamp: string;          // ISO 8601
  operation: 'READ' | 'WRITE' | 'LIST' | 'SEARCH' | 'DELETE';
  command: string;            // Raw command string, e.g. "cat /slack/incident/chat.jsonl"
  mount_path: string;         // e.g. "/slack"
  resource_path: string;      // e.g. "/channels/incident/chat.jsonl"
  resource_type: string;      // e.g. "slack"
  bytes_read: number;
  bytes_written: number;
  cache_hit: boolean;
  latency_ms: number;
  api_calls_made: number;     // Number of backing API calls triggered
  error: string | null;
  metadata: Record<string, unknown>;  // Resource-specific metadata
}
```

**Where to instrument:** The `Workspace.execute()` method is the chokepoint. Every command flows through it. Wrap the executor to emit `TraceEntry` records before and after each command dispatch.

**Storage:** Trace entries need a persistence layer. See [Section 5 — Technical Gaps](#5-technical-gaps--infrastructure-requirements) for database layer requirements.

**Competitive moat depth:** Deep. Requires VFS position.

---

### 3.2 Workspace Memory

**What it is:** Persistent, structured state that survives across agent turns — digests, diffs, and summaries of previously accessed data.

**Why it matters:** Eliminates redundant data re-reads. Instead of re-reading 10,000 Slack messages on every turn, the agent reads a diff of what changed since last access. Saves tokens, reduces latency, improves accuracy.

**Architecture:**

```
Agent requests: cat /slack/incident/chat.jsonl
    ↓
Workspace Memory Layer checks:
    - Has this path been read before in this session?
    - If yes: compute diff against cached version
    - Return: [new_entries_since_last_read] + [summary_of_prior_state]
    ↓
Agent receives focused, incremental data instead of full re-read
```

**Data model:**

```typescript
interface MemoryEntry {
  session_id: string;
  mount_path: string;
  resource_path: string;
  content_hash: string;        // Hash of content at time of read
  last_accessed: string;       // ISO 8601
  access_count: number;
  summary: string | null;      // Agent-relevant summary of content
  schema: Record<string, unknown> | null;  // For structured data (JSON, Parquet, CSV)
}
```

**Implementation approach:**

1. Track content hashes in the existing file cache layer.
2. On re-read of a previously accessed path, compute delta between cached hash and current content.
3. If content unchanged: return a "no changes since last read" signal (saves tokens entirely).
4. If content changed: return only the diff (new lines, modified records).
5. For large files: maintain a rolling summary that updates incrementally.

**Dependencies:** Execution trace (for access history), enhanced file cache (for content hashing).

**Where to build:** Extend the existing cache layer (`RedisFileCacheStore` / `RAMFileCacheStore`) with content hash tracking and diff computation. Add a `MemoryLayer` class that sits between the executor and the cache, intercepting reads and applying diff logic.

**Competitive moat depth:** Deep. Requires both cache control and access history visibility.

---

### 3.3 Dynamic Workspace Manifest

**What it is:** A real-time, structured overview of workspace state that the agent receives at the start of each turn — what data is available, how fresh it is, how large it is, what changed recently.

**Why it matters:** Eliminates the "exploration phase" where agents waste 3-4 turns running `ls` on various mounts to figure out what's available. The manifest lets the agent immediately reason about which mounts to query.

**Output format (included in agent system prompt):**

```
WORKSPACE STATE (as of 2026-05-22T10:30:00Z):

/slack (messaging, READ)
  channels/incident: 12 threads, last activity 4m ago, 3 messages contain "alert"
  channels/engineering: 47 threads today, 2 file attachments

/github (code, READ) — repo: strukto-ai/mirage
  14 files changed in last commit (2h ago), branch: main
  3 open PRs, 1 with failing CI

/linear (project-management, WRITE) — team: eng
  127 open issues, 4 created today, 2 tagged "urgent"

/s3/logs (object-storage, READ) — bucket: prod-logs
  340MB today, growing ~2MB/min, last modified 1m ago
  prefixes: app/, access/, ml-training/
```

**Implementation approach:**

1. The index cache already contains directory listings and metadata for each mount.
2. Build a `ManifestGenerator` that reads the index cache for each mount and produces a structured summary.
3. Extend `ws.file_prompt` (currently static) to call the manifest generator dynamically.
4. Add freshness indicators by comparing index cache timestamps to current time.
5. Add content signals by sampling cached file content (keyword frequency, record counts).

**Where to build:** New module alongside the existing `file_prompt` generation. Should be called lazily (only regenerate when index cache updates) and cached at the workspace level.

**Competitive moat depth:** Medium. Requires unified index cache across mounts.

---

### 3.4 Token-Aware Data Formatting

**What it is:** LLM-optimized output transformations that reduce token consumption while preserving information content. Instead of returning raw file bytes, Mirage returns data formatted for efficient LLM consumption.

**Why it matters:** A 50,000-line log file returned raw will blow the context window. Intelligent truncation with summaries, schema-aware formatting, and de-duplication across pipe stages directly reduce token costs and improve agent accuracy.

**Implementation approach:**

Extend the existing custom command system (`ws.command('cat', { resource, filetype }, handler)`) with built-in LLM-optimized formatters:

```typescript
// Built-in formatters, applied automatically unless overridden
const builtinFormatters = {
  // Large text files: truncate + summarize middle
  'text/plain': (content, opts) => {
    if (content.lines > opts.maxLines) {
      return {
        head: content.slice(0, opts.headLines),
        tail: content.slice(-opts.tailLines),
        summary: summarizeMiddle(content),  // line counts, pattern frequencies
      }
    }
    return content;
  },

  // JSON/JSONL: schema + sample + stats
  'application/jsonl': (content, opts) => ({
    schema: inferSchema(content),
    rowCount: content.length,
    sample: content.slice(0, opts.sampleSize),
    stats: computeFieldStats(content),
  }),

  // Parquet: column metadata + row count + sample
  'application/parquet': (content, opts) => ({
    columns: content.schema.fields.map(f => ({ name: f.name, type: f.type })),
    rowCount: content.numRows,
    sample: content.head(opts.sampleSize).toJSON(),
  }),
};
```

**Configuration:** Workspace-level setting for token budget:

```yaml
formatting:
  token_budget: 4000          # Max tokens per command output
  strategy: summarize         # truncate | summarize | schema-only
  per_mount:
    /s3/logs:
      strategy: summarize
      token_budget: 2000
    /postgres:
      strategy: schema-only   # Return schema + row count, agent requests specific data
```

**Where to build:** Extend the command dispatch layer in the executor. After a resource returns raw content, apply the appropriate formatter before returning to the agent. This is a transformation step between the resource layer and the shell output layer.

**Dependencies:** Need token counting utility (tiktoken or similar). Need schema inference for JSON/JSONL/CSV/Parquet.

**Competitive moat depth:** Medium. High value, but could be built at other layers.

---

### 3.5 Predictive Prefetching

**What it is:** Learn agent access patterns from execution traces and prefetch data from likely-next mounts while the agent processes current data.

**Why it matters:** Turns sequential API calls into parallel ones. If agents in "incident response" workspaces consistently read Slack → GitHub → Datadog, prefetch GitHub and Datadog data while the agent processes Slack data.

**Implementation approach:**

1. Build access pattern model from execution traces (simple Markov chain: given current mount access, what's the probability of accessing each other mount next?).
2. Maintain per-template pattern profiles (incident-response template has different patterns than knowledge-management template).
3. On each command execution, check if the pattern model predicts a likely next access with >70% confidence.
4. If yes, trigger async prefetch into the file cache.
5. When the agent's next command arrives, it hits the cache instead of the network.

```typescript
interface AccessPattern {
  template_id: string;
  from_mount: string;
  to_mount: string;
  probability: number;
  avg_latency_saved_ms: number;
  conditional_signals?: {
    // e.g., "only prefetch GitHub CI if Slack data contains 'deploy'"
    source_keyword: string;
    confidence_boost: number;
  }[];
}
```

**Where to build:** New `PrefetchEngine` that subscribes to execution trace events and triggers async cache warming. Should be a separate async process/worker that doesn't block the main executor.

**Dependencies:** Execution trace (for pattern learning), enhanced cache layer (for async write).

**Competitive moat depth:** Deep. Requires both access pattern visibility and cache control.

---

### 3.6 Semantic Bookmarks & Annotations

**What it is:** Named references to specific data locations that persist across turns. Agents can bookmark important findings and annotate them with notes for future reference.

**Why it matters:** Gives agents addressable memory not bound to the LLM context window. The workspace becomes a persistent scratchpad that accumulates knowledge across agent runs.

**Interface:**

```bash
# Create a bookmark
bookmark /slack/channels/incident/thread-1684331234 as "root-cause-thread"

# Read a bookmark
cat @root-cause-thread

# Annotate a bookmark
annotate @root-cause-thread "Payment gateway timeout caused by connection pool exhaustion"

# List bookmarks
ls @bookmarks
```

**Data model:**

```typescript
interface Bookmark {
  name: string;
  target_path: string;
  created_at: string;
  created_by: string;     // agent session ID
  annotations: {
    text: string;
    timestamp: string;
    author: string;
  }[];
  content_hash: string;   // Hash at time of bookmark creation
  stale: boolean;          // true if target content has changed since bookmark
}
```

**Where to build:** New shell command implementations (`bookmark`, `annotate`) registered in the executor. Bookmark storage lives in the workspace state (RAM or Redis, depending on cache backend). Bookmarks serialize into snapshots so they persist across workspace clone/restore.

**Competitive moat depth:** Medium. Valuable but conceptually replicable.

---

### 3.7 Mount-Aware Tool Selection Hints

**What it is:** Lightweight, structured metadata per mount that helps agents choose the right mount without exploration.

**Implementation:**

```typescript
interface MountHint {
  path: string;
  resource_type: string;
  semantic_type: 'messaging' | 'code' | 'storage' | 'database' | 'project-management' | 'documentation' | 'observability';
  contains: string[];          // ["conversations", "threads", "files"]
  freshness: 'real-time' | 'near-real-time' | 'periodic' | 'static';
  mode: 'READ' | 'WRITE' | 'READ_WRITE';
  size_hint: string;           // "~340MB", "127 issues", "12 channels"
  last_activity: string;       // Relative timestamp
}
```

**Where to build:** Extend `ws.file_prompt` generation. Each resource implementation should expose a `getHints()` method that returns structured metadata from the index cache.

**Competitive moat depth:** Shallow. But important for DX.

---

## 4. Feature Vision: Track 2 — Governance & Auditability

> **Goal:** Mirage becomes the single control plane for enterprise agent data access — auditable, policy-enforced, and compliant.

### 4.1 Policy Engine

**What it is:** Declarative rules that control what agents can do within a workspace — which mounts allow reads/writes, what data patterns are blocked, what operations require human approval.

**Policy schema:**

```yaml
# workspace-policy.yaml
version: "1.0"
policies:
  mount_access:
    - mount: /slack/*
      mode: READ
      auto_approve: true
    - mount: /linear/*
      mode: WRITE
      auto_approve: false              # Requires human approval for writes
      approval_channel: "slack:#agent-approvals"
    - mount: /s3/production/*
      mode: READ
      max_read_mb_per_session: 100     # Budget control
    - mount: /postgres/customers/*
      mode: DENY                       # Block entirely

  data_classification:
    scan_on_read: true
    scan_on_write: true
    patterns:
      - type: email_address
        action: redact                 # Replace with [REDACTED_EMAIL]
      - type: ssn
        action: block                  # Block the operation, log the attempt
      - type: api_key
        action: alert                  # Allow but flag in audit trail

  budgets:
    per_session:
      max_api_calls: 500
      max_data_read_mb: 200
      max_estimated_cost_usd: 5.00
    on_exceed: pause_and_alert

  data_residency:
    rules:
      - source: /slack/*
        allowed_destinations: [/linear/*, /data/*]
        blocked_destinations: [/s3/us-east-*]
```

**Architecture:**

```
Agent issues command
    ↓
Shell parser produces AST
    ↓
Policy Engine evaluates command against policy rules:
    1. Mount access check (allowed? denied? requires approval?)
    2. Budget check (within limits?)
    3. If approved or auto-approve: proceed to executor
    4. If requires approval: pause, emit approval request, wait
    5. After execution: scan output for data classification patterns
    6. If write: scan write payload before committing
    ↓
Executor dispatches to resource
    ↓
Post-execution: emit trace entry with policy evaluation results
```

**Where to build:** New `PolicyEngine` class that sits between the shell parser and the command executor. The engine loads policy from a YAML config (workspace-level) and evaluates each command against it before dispatch. This is a middleware insertion point in the existing execute pipeline.

**Key implementation detail:** The policy engine must be synchronous in the evaluation path (don't add latency to reads that are auto-approved) but support async approval flows (pause execution, emit webhook/Slack message, wait for response).

**Dependencies:** Execution trace (for logging policy decisions), data classification scanner (for PII detection).

---

### 4.2 Data Classification Scanner

**What it is:** A scanning layer that detects PII, credentials, and other sensitive data patterns in content flowing through the workspace — both reads (data going to the agent) and writes (data the agent sends to services).

**Architecture:**

```
Data flows through workspace (read or write)
    ↓
Classification Scanner examines content:
    - Regex patterns (SSN, credit card, email, phone)
    - Keyword patterns (API keys, tokens, passwords)
    - Configurable custom patterns (company-specific)
    ↓
Scanner returns classification result:
    - clean: no sensitive data found
    - flagged: sensitive data found, with types and locations
    ↓
Policy engine applies action based on classification + policy rules
```

**Implementation approach:**

```typescript
interface ClassificationResult {
  clean: boolean;
  findings: {
    type: string;           // "email_address", "ssn", "api_key", etc.
    confidence: number;     // 0-1
    location: {
      line: number;
      column: number;
      length: number;
    };
    redacted_value: string; // "[REDACTED_EMAIL]"
  }[];
}

interface ClassificationScanner {
  scan(content: string | Buffer, patterns: PatternConfig[]): ClassificationResult;
  redact(content: string, findings: Finding[]): string;  // Apply redactions
}
```

**Where to build:** New module that the policy engine calls. Should be fast (regex-based for v1, model-based for v2) and configurable. The scanner is invoked by the policy engine at two points: after a read (before returning data to the agent) and before a write (before sending data to the resource).

**Competitive moat depth:** Deep. Only the VFS layer can scan all data flows in one place.

---

### 4.3 Cost Attribution

**What it is:** Track the real cost of agent operations — API calls to backing services, data transfer, cache misses — and attribute them to workspaces, sessions, teams, and templates.

**Data model:**

```typescript
interface CostEntry {
  trace_id: string;
  session_id: string;
  workspace_id: string;
  template_id: string | null;
  team_id: string | null;
  mount_path: string;
  resource_type: string;
  operation: string;
  api_calls: number;
  data_bytes: number;
  cache_hit: boolean;
  estimated_cost_usd: number;  // Based on known pricing (S3 GET = $0.0004/1000, etc.)
  timestamp: string;
}
```

**Where to build:** Extend the execution trace to include cost estimation. Each resource implementation needs a `estimateCost(operation, bytes)` method that returns estimated cost based on the service's known pricing. Aggregate in the trace storage layer.

---

### 4.4 Session Forensics & Replay

**What it is:** Full reconstruction of any agent session — what data was read, what was written, what policies were evaluated, what the agent produced — with the ability to replay the session in a sandboxed workspace.

**Architecture:**

```
Session forensics query: "Show me session abc-123"
    ↓
Load execution trace for session abc-123
    ↓
Reconstruct timeline:
    - Commands executed (in order)
    - Data read (from trace + file cache snapshots)
    - Data written (from trace)
    - Policy decisions (from trace)
    - Approval flows (from trace)
    ↓
Optional: Replay
    - Load workspace snapshot from session start
    - Re-execute commands in sequence
    - Compare outputs to original trace
    - Highlight divergences
```

**Dependencies:** Execution trace, snapshot/clone (already shipped), file cache with content retention for forensic lookups.

**Where to build:** New `ForensicsEngine` that queries the trace storage and assembles session timelines. Replay uses the existing workspace clone/snapshot infrastructure with the trace as a command playbook.

---

### 4.5 Anomaly Detection

**What it is:** Baseline normal agent behavior from execution traces, alert when an agent deviates significantly.

**Detection patterns:**

| Anomaly | Signal | Detection Method |
|---|---|---|
| Data volume spike | Agent reads 100x more data than average | Statistical threshold on bytes_read per session |
| Novel mount access | Agent accesses a mount it's never used before | Set comparison against historical mount access per template |
| Off-hours activity | Agent writes to production systems at unusual time | Time-of-day distribution analysis |
| Topic drift | Incident agent suddenly reading HR/finance data | Mount type classification vs. expected template behavior |
| Rapid-fire operations | Agent executing commands at abnormal rate | Rate analysis on trace timestamps |

**Where to build:** Background worker that processes execution traces and maintains per-template behavioral baselines. Alert emission via webhook/Slack when anomalies are detected.

**Dependencies:** Execution trace (sufficient historical data for baseline), trace storage with efficient aggregation queries.

---

### 4.6 Access Control Graph

**What it is:** Organization-level visibility into who (teams, users) can access what (mounts, services) through which agents (workspaces, templates), with policy annotations at each edge.

**Data model:**

```typescript
interface AccessGraph {
  teams: Team[];
  workspaces: WorkspaceNode[];
  mounts: MountNode[];
  edges: {
    team_to_workspace: { team_id: string; workspace_id: string; role: string }[];
    workspace_to_mount: { workspace_id: string; mount_path: string; mode: string; policy_id: string }[];
  };
}
```

**Where to build:** API endpoint that aggregates workspace configurations, mount definitions, and policy rules into a graph structure. UI visualization is a future concern — the data model and API come first.

---

## 5. Technical Gaps & Infrastructure Requirements

### GAP 1: Persistent Storage Layer (Critical)

**Current state:** Mirage has no persistent storage beyond the file/index cache (RAM or Redis). Execution traces, workspace memory, bookmarks, policy evaluations, cost data, and forensic records all need durable, queryable storage.

**What's needed:** A lightweight, embeddable database layer that:

- Stores execution trace entries (append-heavy, time-series-like)
- Stores workspace memory entries (key-value with metadata)
- Stores bookmark and annotation data (small, structured records)
- Stores policy evaluation logs (append-only audit log)
- Supports efficient time-range queries (for forensics: "show me all traces from session X")
- Supports aggregation queries (for anomaly detection: "average bytes_read per session for template Y")
- Embeds in-process (no external dependency for single-process mode)
- Optionally delegates to an external store (Postgres, Redis, or a managed service for multi-replica deployments)

**Recommended approach:**

```
Tier 1 (embedded, default): SQLite
    - Single-file database, zero configuration
    - Sufficient for single-process workspaces and local development
    - WAL mode for concurrent read/write
    - Good enough for traces, memory, bookmarks, policies

Tier 2 (shared, production): Postgres or ClickHouse
    - For multi-replica deployments (serverless, multi-worker services)
    - Time-series optimized for trace data (ClickHouse) or
      general-purpose with good JSON support (Postgres)
    - Connection pooling via the existing Redis infrastructure pattern

Tier 3 (managed, enterprise): Cloud-hosted trace/audit storage
    - For the managed Mirage Cloud product (future)
    - Could be a dedicated service or integration with existing
      observability platforms (Datadog, Grafana)
```

**Implementation guidance:**

- Define a `StorageBackend` interface with implementations for SQLite, Postgres, and Redis
- Follow the same pattern as the existing cache backends (`RAMFileCacheStore`, `RedisFileCacheStore`)
- All trace/memory/policy writes should be async and non-blocking to avoid adding latency to the command execution path
- The storage layer should be optional — Mirage should still work without it (traces just don't persist)

```typescript
interface StorageBackend {
  // Trace operations
  appendTrace(entry: TraceEntry): Promise<void>;
  queryTraces(filter: TraceFilter): Promise<TraceEntry[]>;

  // Memory operations
  getMemory(sessionId: string, path: string): Promise<MemoryEntry | null>;
  setMemory(entry: MemoryEntry): Promise<void>;

  // Bookmark operations
  getBookmark(name: string): Promise<Bookmark | null>;
  setBookmark(bookmark: Bookmark): Promise<void>;
  listBookmarks(prefix?: string): Promise<Bookmark[]>;

  // Policy log operations
  appendPolicyLog(entry: PolicyLogEntry): Promise<void>;
  queryPolicyLogs(filter: PolicyLogFilter): Promise<PolicyLogEntry[]>;

  // Aggregation (for anomaly detection, cost attribution)
  aggregate(query: AggregationQuery): Promise<AggregationResult>;
}
```

**Files to modify:**

- New: `python/mirage/storage/` directory with `base.py`, `sqlite.py`, `postgres.py`
- New: `typescript/packages/core/src/storage/` with equivalent implementations
- Modify: `Workspace` constructor to accept optional `StorageBackend`
- Modify: `Workspace.execute()` to emit trace entries to storage backend

---

### GAP 2: Middleware Pipeline in the Executor (Critical)

**Current state:** The executor dispatches commands directly from the shell parser to the resource handlers. There's no middleware insertion point for policy evaluation, data classification, trace emission, or memory layer operations.

**What's needed:** A middleware pipeline pattern in the executor:

```
Shell Parser (AST)
    ↓
Middleware Pipeline:
    1. Policy Engine       → evaluate access rules, check budgets, handle approvals
    2. Memory Layer        → check for cached state, compute diffs for re-reads
    3. Prefetch Engine     → trigger async prefetch based on access patterns
    ↓
Command Dispatch (to resource handler)
    ↓
Post-Dispatch Middleware:
    4. Data Classifier     → scan output for PII/sensitive data, apply redactions
    5. Token Formatter     → apply LLM-optimized formatting
    6. Trace Emitter       → write execution trace entry
    7. Memory Updater      → update workspace memory state
    8. Cost Tracker        → estimate and record cost
```

**Implementation guidance:**

```typescript
type Middleware = (
  context: ExecutionContext,
  next: () => Promise<ExecutionResult>
) => Promise<ExecutionResult>;

class MiddlewarePipeline {
  private middlewares: Middleware[] = [];

  use(middleware: Middleware): void {
    this.middlewares.push(middleware);
  }

  async execute(context: ExecutionContext): Promise<ExecutionResult> {
    // Build chain from inside out
    let handler = context.dispatch;
    for (const mw of [...this.middlewares].reverse()) {
      const next = handler;
      handler = () => mw(context, next);
    }
    return handler();
  }
}
```

**Files to modify:**

- Refactor: `Workspace.execute()` to use middleware pipeline instead of direct dispatch
- New: `python/mirage/middleware/` and `typescript/packages/core/src/middleware/` directories
- Each feature (policy, memory, trace, formatting, etc.) implements the `Middleware` interface

---

### GAP 3: Credential Management (Important)

**Current state:** Each resource handles authentication independently. Users configure credentials per-resource in code or environment variables.

**What's needed:** Workspace-level credential management:

```typescript
interface CredentialStore {
  get(resourceType: string, scope?: string): Promise<Credential>;
  set(resourceType: string, credential: Credential): Promise<void>;
  refresh(resourceType: string): Promise<Credential>;  // Token refresh
  rotate(resourceType: string): Promise<void>;          // Credential rotation
}

interface Credential {
  type: 'oauth2' | 'api_key' | 'basic' | 'ssh_key' | 'service_account';
  value: Record<string, string>;   // Opaque credential data
  expires_at: string | null;
  scopes: string[];
  last_refreshed: string;
}
```

**Implementation guidance:**

- Build a `CredentialStore` that wraps credential management for all resources
- Support encrypted-at-rest credential storage (use OS keychain for local, Vault/KMS for production)
- Resources should accept credentials from the store instead of from their own config
- Token refresh should be automatic and transparent — resources shouldn't handle OAuth refresh flows themselves

**Files to modify:**

- New: `python/mirage/credentials/` and `typescript/packages/core/src/credentials/`
- Modify: Each resource's constructor to accept optional `CredentialStore` injection
- Modify: Resource config classes to support credential references instead of inline values

---

### GAP 4: Workspace Template System (Important)

**Current state:** Workspaces are created programmatically in code or via CLI YAML config. No template catalog, no inheritance, no organizational defaults.

**What's needed:**

```yaml
# templates/incident-response.yaml
name: incident-response
version: "1.2"
description: "Cross-service incident triage workspace"
mounts:
  /slack:     { resource: slack, mode: READ }
  /github:    { resource: github, mode: READ }
  /linear:    { resource: linear, mode: WRITE }
  /pagerduty: { resource: pagerduty, mode: READ }
  /data:      { resource: ram, mode: WRITE }
policy: policies/incident-response-policy.yaml
credentials: credentials/team-sre.yaml
manifest:
  refresh_interval: 30s
  include_content_signals: true
memory:
  enabled: true
  diff_mode: incremental
formatting:
  token_budget: 4000
  strategy: summarize
```

**Implementation guidance:**

- Templates are YAML files that define a complete workspace configuration
- Templates can inherit from other templates (`extends: base-readonly`)
- Organization-level defaults can be set in a root template
- Template resolution: CLI `mirage workspace create --template incident-response` loads the template, merges with org defaults, validates, and creates the workspace
- Template catalog is a directory of YAML files (local or fetched from a registry)

---

### GAP 5: Content Hashing in Cache Layer (Moderate)

**Current state:** The file cache stores raw bytes. It doesn't track content hashes or support diff computation.

**What's needed for workspace memory and provenance:**

- Store SHA-256 content hash alongside cached content
- On cache update (content changed), retain the previous hash for diff computation
- Support content-addressable lookup (given a hash, retrieve the content)
- Support diff computation between two content versions

**Files to modify:**

- Modify: `RAMFileCacheStore` and `RedisFileCacheStore` to store content hashes
- New: `ContentDiffer` utility that computes diffs between two versions of a cached file
- Modify: Cache eviction logic to optionally retain hashes (even after content is evicted) for memory/provenance tracking

---

### GAP 6: Async Event System (Moderate)

**Current state:** No event system. Components can't subscribe to workspace events.

**What's needed:** A lightweight pub/sub system within the workspace for:

- Trace emission (executor → trace storage)
- Policy evaluation events (policy engine → audit log)
- Cache events (cache layer → prefetch engine)
- Approval requests (policy engine → external webhook/Slack)
- Anomaly alerts (anomaly detector → external webhook)

```typescript
interface WorkspaceEventBus {
  emit(event: WorkspaceEvent): void;
  on(eventType: string, handler: (event: WorkspaceEvent) => void): void;
  off(eventType: string, handler: (event: WorkspaceEvent) => void): void;
}

type WorkspaceEvent =
  | { type: 'trace'; entry: TraceEntry }
  | { type: 'policy_evaluation'; result: PolicyResult }
  | { type: 'cache_miss'; mount: string; path: string }
  | { type: 'approval_required'; command: string; mount: string }
  | { type: 'anomaly_detected'; anomaly: AnomalyReport }
  | { type: 'budget_exceeded'; budget: BudgetStatus };
```

**Files to modify:**

- New: `python/mirage/events.py` and `typescript/packages/core/src/events.ts`
- Modify: `Workspace` constructor to create event bus
- Modify: Middleware pipeline to emit events at appropriate points

---

## 6. Build-Out Plan & Phasing

### Phase 1: Foundation (Weeks 1-6)

**Goal:** Build the infrastructure that every subsequent feature depends on.

| Week | Deliverable | Dependencies |
|---|---|---|
| 1-2 | **Execution Trace** — Instrument `Workspace.execute()` to emit `TraceEntry` records. In-memory storage (append to array) for v1. | None |
| 2-3 | **Storage Backend (SQLite)** — Implement `StorageBackend` interface with SQLite backend. Migrate trace storage from in-memory to SQLite. | Trace |
| 3-4 | **Middleware Pipeline** — Refactor executor to use middleware chain. Move trace emission to middleware. | Trace |
| 4-5 | **Content Hashing** — Add SHA-256 hashing to file cache layer. Store hashes alongside content. | Cache layer |
| 5-6 | **Event Bus** — Implement workspace event system. Connect trace middleware to event bus. | Middleware pipeline |

**Validation:** At the end of Phase 1, every command executed in a workspace produces a structured trace entry stored in SQLite, accessible via API. The middleware pipeline is in place for subsequent features to plug into.

### Phase 2: Agent Performance (Weeks 6-14)

**Goal:** Ship features that make agents measurably better on Mirage.

| Week | Deliverable | Dependencies |
|---|---|---|
| 6-8 | **Dynamic Workspace Manifest** — Replace static `file_prompt` with dynamic manifest generated from index cache. | Index cache |
| 8-10 | **Workspace Memory** — Implement memory layer middleware. Diff computation for re-reads. "No changes" short-circuit. | Content hashing, middleware pipeline |
| 10-12 | **Token-Aware Formatting** — Built-in formatters for common file types (JSONL, CSV, Parquet, large text). Token budget configuration. | Middleware pipeline |
| 12-14 | **Semantic Bookmarks** — Bookmark and annotate commands. Bookmark storage in SQLite. | Storage backend |

**Validation:** Run a benchmark comparing agent performance (task completion rate, tokens consumed, wall-clock time) on a cross-service triage task, with and without Phase 2 features. Publish results.

### Phase 3: Governance (Weeks 12-20)

**Goal:** Ship enterprise governance features that unlock enterprise sales.

| Week | Deliverable | Dependencies |
|---|---|---|
| 12-14 | **Policy Engine (v1)** — Mount access rules, write approval flows, budget controls. Policy loaded from YAML. | Middleware pipeline, event bus |
| 14-16 | **Data Classification Scanner** — Regex-based PII/sensitive data detection. Redact/block/alert actions. | Middleware pipeline, policy engine |
| 16-18 | **Cost Attribution** — Per-resource cost estimation. Aggregation by workspace/session/team. | Trace storage, storage backend (aggregation queries) |
| 18-20 | **Session Forensics** — Timeline reconstruction from traces. Replay in sandboxed workspace. | Trace storage, snapshot/clone |

**Validation:** Demonstrate to a pilot enterprise customer: create a workspace with a policy that blocks PII exfiltration, run an agent session, show the full audit trail, replay the session forensically.

### Phase 4: Intelligence (Weeks 18-26)

**Goal:** Ship features that create deep competitive moat.

| Week | Deliverable | Dependencies |
|---|---|---|
| 18-20 | **Predictive Prefetching** — Access pattern learning from traces. Async prefetch into cache. | Trace storage (historical data), cache layer |
| 20-22 | **Cross-Mount Data Provenance** — Track data lineage across pipe stages. Attach provenance metadata to writes. | Middleware pipeline, trace storage |
| 22-24 | **Anomaly Detection** — Behavioral baselines from traces. Statistical anomaly alerting. | Trace storage (sufficient history), event bus |
| 24-26 | **Credential Management** — Workspace-level credential store. Auto-refresh, rotation. | Resource layer refactoring |

### Phase 5: Enterprise Platform (Weeks 24-36)

**Goal:** Ship the enterprise product.

| Week | Deliverable | Dependencies |
|---|---|---|
| 24-28 | **Workspace Templates** — Template catalog, inheritance, organizational defaults. | All prior features |
| 28-32 | **Access Control Graph** — Organization-level visibility. Team → workspace → mount → policy mapping. | Policy engine, storage backend |
| 32-36 | **Storage Backend (Postgres)** — Production-grade storage for multi-replica deployments. Migration tooling from SQLite. | SQLite backend (schema stabilized) |

---

## 7. Implementation Notes for Coding Agents

### Key Architectural Principles

1. **Non-blocking by default.** Trace emission, memory updates, cost tracking, and event emission must never add latency to the command execution hot path. Use async writes and fire-and-forget patterns for all observability data. Only the policy engine (access check, budget check) is synchronous — and even that should be fast (in-memory policy evaluation).

2. **Optional by default.** Every new feature should be opt-in. A workspace with no storage backend, no policy, no memory, and no formatting should behave identically to the current implementation. Features activate when configured.

3. **Same interface, Python and TypeScript.** Every feature must be implemented in both SDKs. Define the interface in TypeScript (as the source of truth for type definitions), then implement equivalently in Python. The middleware pipeline, storage backend, and event bus interfaces should be identical across languages.

4. **Test with real agent workloads.** Unit tests are necessary but insufficient. Each feature needs an integration test that runs an actual agent (OpenAI Agents SDK or Vercel AI SDK) against a workspace with the feature enabled, and validates that the agent's behavior improves (or that the governance feature correctly blocks/logs/alerts).

### File Organization for New Code

```
python/mirage/
├── storage/
│   ├── __init__.py
│   ├── base.py              # StorageBackend interface
│   ├── sqlite.py            # SQLite implementation
│   └── postgres.py          # Postgres implementation (Phase 5)
├── middleware/
│   ├── __init__.py
│   ├── pipeline.py          # MiddlewarePipeline class
│   ├── trace.py             # Trace emission middleware
│   ├── policy.py            # Policy engine middleware
│   ├── memory.py            # Workspace memory middleware
│   ├── classifier.py        # Data classification middleware
│   ├── formatter.py         # Token-aware formatting middleware
│   ├── prefetch.py          # Predictive prefetch middleware
│   ├── provenance.py        # Data provenance middleware
│   └── cost.py              # Cost attribution middleware
├── policy/
│   ├── __init__.py
│   ├── engine.py            # Policy evaluation engine
│   ├── schema.py            # Policy YAML schema (Pydantic models)
│   └── classifier.py        # PII/sensitive data scanner
├── credentials/
│   ├── __init__.py
│   ├── store.py             # CredentialStore interface + implementations
│   └── refresh.py           # Token refresh logic
├── templates/
│   ├── __init__.py
│   ├── loader.py            # Template YAML loading + inheritance
│   └── catalog.py           # Template registry
├── forensics/
│   ├── __init__.py
│   ├── timeline.py          # Session timeline reconstruction
│   └── replay.py            # Session replay engine
├── events.py                # WorkspaceEventBus
└── manifest.py              # Dynamic workspace manifest generator

typescript/packages/core/src/
├── storage/
│   ├── index.ts
│   ├── types.ts             # StorageBackend interface
│   ├── sqlite.ts            # SQLite implementation (via better-sqlite3)
│   └── postgres.ts          # Postgres implementation (Phase 5)
├── middleware/
│   ├── index.ts
│   ├── pipeline.ts
│   ├── trace.ts
│   ├── policy.ts
│   ├── memory.ts
│   ├── classifier.ts
│   ├── formatter.ts
│   ├── prefetch.ts
│   ├── provenance.ts
│   └── cost.ts
├── policy/
│   ├── index.ts
│   ├── engine.ts
│   ├── schema.ts
│   └── classifier.ts
├── credentials/
│   ├── index.ts
│   ├── store.ts
│   └── refresh.ts
├── templates/
│   ├── index.ts
│   ├── loader.ts
│   └── catalog.ts
├── forensics/
│   ├── index.ts
│   ├── timeline.ts
│   └── replay.ts
├── events.ts
└── manifest.ts
```

### Critical Refactoring Required

1. **`Workspace.execute()` refactoring** (both Python and TypeScript): The current execute method likely dispatches directly to resource handlers. This needs to be refactored to pass through the middleware pipeline. This is the single most important refactoring — it's the foundation for every new feature.

2. **Cache layer enhancement**: The existing `RAMFileCacheStore` and `RedisFileCacheStore` need to be extended with content hashing. This is additive (new fields, new methods) and should not break existing behavior.

3. **Resource interface extension**: Each resource implementation needs new optional methods: `estimateCost()`, `getHints()`, and optionally `getCredentialRequirements()`. These should be optional with sensible defaults so existing resources don't break.

4. **`file_prompt` replacement**: The current static `ws.file_prompt` needs to be replaced with a dynamic `ws.getSystemPrompt()` method that calls the manifest generator. The static version should remain as a fallback when the manifest generator is not configured.

### Environment & Dependencies

**Python (new dependencies):**
- `aiosqlite` — async SQLite for trace/memory storage
- `tiktoken` — token counting for formatting
- `pyyaml` — policy/template YAML parsing (likely already a dependency)
- `cryptography` — credential encryption at rest (optional)

**TypeScript (new dependencies):**
- `better-sqlite3` — embedded SQLite for Node.js
- `tiktoken` or `gpt-tokenizer` — token counting
- `yaml` — policy/template YAML parsing (likely already a dependency)

**No new external service dependencies** for Phase 1-4. All features run in-process with SQLite. Postgres and Redis are optional production-grade backends added in Phase 5.

---

## Appendix: Feature-to-Moat Mapping

| Feature | Moat Depth | Requires VFS Position | Track |
|---|---|---|---|
| Execution Trace | Deep | Yes | Both |
| Workspace Memory | Deep | Yes | Performance |
| Cross-Mount Data Provenance | Deep | Yes | Both |
| PII Detection in Transit | Deep | Yes | Governance |
| Predictive Prefetching | Deep | Yes | Performance |
| Session Forensics + Replay | Deep | Yes | Governance |
| Dynamic Workspace Manifest | Medium | Yes | Performance |
| Token-Aware Formatting | Medium | Partially | Performance |
| Cost Attribution | Medium | Partially | Governance |
| Anomaly Detection | Medium | Partially | Governance |
| Workspace Templates | Shallow | No | DX |
| Credential Management | Shallow | No | DX |
| Data Residency Routing | Shallow | No | Governance |
| Access Control Graph | Shallow | No | Governance |
| Semantic Bookmarks | Medium | Partially | Performance |
| Mount Selection Hints | Shallow | No | Performance |
