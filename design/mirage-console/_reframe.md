# Mirage Console — REFRAME (read this first)

The product is being **re-scoped**. Earlier research produced a strong "trace viewer + investigation/governance" design. The user has pivoted the framing. Honor the NEW framing below; reuse the still-valid data grounding further down.

## NEW PRODUCT FRAMING (the pivot — non-negotiable)

> "I want this to be a **developer debug console**, like the **Redux DevTools console**, or any other developer-facing dev tool, that can see **ALL the traces within a mirage workspace**, and also offer **connected data-source exploration**."

Three consequences that reshape the design:

1. **It is a developer dev-tool, not an ops/governance product.** Feel: Redux DevTools / Chrome DevTools / a language debugger — dense, fast, keyboard-friendly, made for an engineer staring at it all day. **Demote governance hard**: no persistent pending-effects counter, no global LIVE red-chrome, no typed-PROMOTE modal, no "investigations inbox" front door. Effect class / reversibility survive only as quiet per-write decorations.

2. **The WORKSPACE is the top-level container.** The console scopes to a mirage workspace and shows **ALL traces/runs and ALL events** flowing through it — not a cross-session ops inbox. A workspace switcher sits at the top; everything below is "everything that happened in this workspace."

3. **Two new first-class pillars** join the trace waterfall:
   - **Event Log + Time-Travel (the Redux-DevTools centerpiece).** A unified, chronological, filterable **action stream** of *everything* in the workspace (AG-UI run/step/reasoning/tool-call events + VfsOps + relay StreamEvents + mock backend requests), with a **time-travel cursor**: select any action and the right pane shows the **reconstructed workspace state at that moment** (VFS overlay, mounts, what's been read/written, pending effects) with **diff highlighting of what changed at that action**. Borrow Redux DevTools directly: action list, state tree inspector, action diff, jump-to/skip, future-dimming of not-yet-executed actions, import/export.
   - **Connected Data-Source Exploration.** Browse the workspace's mounted backends (S3, Slack, GitHub, Postgres, Datadog, finance, customers, …) as a live catalog/VFS tree: per-source status/type/mode/consistency, browse paths/files/records/tables, preview content + schema, show fingerprint/revision/size, and — the moat tie-in — **reverse-link from any data path to "which traces/steps touched this"** (read/wrote it). This turns data exploration bidirectional with the trace spine.

Keep the best of the prior design that still fits a dev tool: the **single-run Trace waterfall + correlated inspector** (the VfsOp ground-truth leaf, drift flag, latency-phase bars, click-to-cross-highlight), per-node **permalinks**, and **Compare** (lighter). The prior "Investigation evidence object" and "Workspaces build/promote" become minor/optional, not pillars.

## THE DATA SPINE (still valid — build on this)

```
Session (≈ workspace/branch; thread_id)
 └─ Run (run-{uuid}; one user turn; the trace root)  ── joins ScoreCard · Span tree · relay events by run_id
     └─ Step (step-N; one agent-loop iteration; holds reasoning + tool_call_ids[])
         ├─ Reasoning (THINKING_*/TEXT_*)
         └─ ToolCall (tc-{uuid}; tool_name='exec'; args=raw shell; result=stdout+exit_code)  == one Workspace.execute()
             └─ VfsOp (OpRecord: op·path·source·bytes·duration_ms·mount_prefix·fingerprint·revision·is_cache)  ← THE GROUND-TRUTH LEAF (the moat)
                 └─ decorations: EffectClass · CaptureState · Cache/Latency phase · [Lineage · Policy — reserved]
```

The **one engineering fix** that unblocks correlation (Phase 0): stamp `tool_call_id`/`step_id`/`run_id` + the dropped `source/duration_ms/fingerprint/revision` onto every VfsOp at emission (`server.py` ~L1403), consume `ExecutionNode.records` instead of length-diffing `ws.ops.records`, fill `vfs_ops.tool_call_id` in the coalescer. Until then label op→step attribution `inferred`.

## KEY DATA ENTITIES RELEVANT TO THE NEW PILLARS

- **Relay StreamEvent feed** (`server.py` `_emit_event`/`_persist_and_broadcast`; `stream_events` table; `/events` SSE; `useEventStream`): a flat, monotonic-`seq`-ordered firehose. Union by `.type`: `command{command,exit_code,stdout,cwd,agent,session}`, `op{op,path,source,bytes,duration_ms,mount_prefix,fingerprint,revision,agent,session}`, `mcp_tool_call`, `mock_request{service,method,path,status_code,response_bytes,duration_ms}`, `agent_status`, `agent_thinking`, `console_*`. **This is the raw material for the Redux-style action log.**
- **AG-UI events** (`server.py` stream; `aguiEventReducer.ts`; `types/agui.ts`): RUN/STEP/TEXT_MESSAGE/THINKING/TOOL_CALL_*/CUSTOM(vfs_op)/STATE_SNAPSHOT/STATE_DELTA.
- **OverlayDiff / snapshots / OpRecord** for **time-travel state reconstruction**: `OverlayDiff` (mounts[]→changes[]{op,path,bytes,timestamp}), workspace `snapshot/{drift,state,manifest}`, and the per-op `fingerprint/revision`. STATE_SNAPSHOT/STATE_DELTA AG-UI events exist (Redux-like).
- **Mount** (`vendor/mirage/.../workspace/mount/mount.py`): prefix, resource, mode(READ/WRITE/EXEC), consistency(LAZY/ALWAYS), revisions{path→rev}, resource.is_remote, resource.SUPPORTS_SNAPSHOT. ~30 resource backends in `vendor/mirage/.../resource/`.
- **FileStat**: name, size, modified, fingerprint, revision, type, extra. **VFS browse today is string-parsed `ls -la`/`cat`** (brittle, text-only) — the Data Sources explorer must tolerate that or move to a structured FS read.
- **catalog-proxy package** (`packages/catalog-proxy/`): Iceberg / Snowflake / MCP adapters — schema/table catalog surface for queryable sources.
- **Existing reusable frontend**: `VFSExplorer.tsx`, `DataBrowser.tsx` (data catalog), `TraceExplorer.tsx` (a COMPLETE span waterfall routed nowhere), `RunTracePanel/StepCard/ToolCallRow/ReasoningBlock`, `TrajectoryPage` (best op log), `useEventStream`, `getSessionTrace`/`listSessions`/`replayAguiEvents`, `arcadia_store`.
- **ScoreCard** (offline; join by run_id): gates, TrajectoryMetrics (n_ops, bytes, cache_hit_rate, tokens, cost, within_budget), judge scores+rationale, failure_modes.

## FEASIBILITY (honesty rules — render solid vs inferred vs not-yet-emitted)

- BUILDABLE NOW: the full Session›Run›Step›ToolCall waterfall + reasoning + args/results + run rollups (reducer+store+replay exist); run/session list (`listSessions`/`getSessionTrace`); step→data cross-highlight (dead hooks exist); the relay firehose action log (`useEventStream` + `stream_events`).
- NEEDS SMALL PLUMBING: exact VfsOp→ToolCall correlation (Phase 0 above); surface dropped `fingerprint/revision/source/duration_ms`; join Span tree to real sessions (today a 20-cmd `demo-agent` demo); join ScoreCard by run_id.
- TIME-TRAVEL is PARTIAL: exact for reads-so-far + overlay/pending-effects (op-by-op derivable); **written-mount backing is pinned at stand-up and NOT re-derivable per-tick** — label backing "pinned at stand-up", never promise byte-exact full-FS time travel.
- CACHE HITS emit no OpRecord — "served from cache" / cache-lookup phase is **derived** (`is_cache`==ram / absence of network op / Span `cache_hits`). Label derived.
- DATA-SOURCE BROWSE: string-parsed `ls -la`/`cat`; content preview/diff must label "preview only / binary / truncated". Queryable schema comes via catalog-proxy adapters (Iceberg/Snowflake/MCP).
- NOT BUILDABLE (reserve "not yet emitted" placeholders, never fake): lineage/provenance graph (OpenLineage emit_* NotImplementedError), policy/ACL/budget decisions (PolicyEngine never called at VFS boundary), credential/token lifecycle (broker stubs), PII findings (none).
- STRUCTURAL: `tool_name` is always `'exec'` with a raw shell arg — classify read/write/external via the VfsOp/effect-class layer, not the tool schema.
- SCALE: don't ship on the 2000-event RAM ring or localStorage; standardize on `arcadia_store` with pagination/virtualization. A dev console watching ALL workspace events especially needs this.

## UNIQUE LEVERAGE (why only mirage can build this)

Mirage sits *between the agent's reasoning and the actual data plane* — it observes ground truth (real path/bytes/source/cache/fingerprint at `observe.context.record()`), not the model's self-reported tool args. Every competitor (LangSmith/Langfuse/Phoenix/Helicone/OTel) records only what the wrapper logged; if the agent lies/paraphrases/truncates, their trace is silently wrong. Exploit this five ways: (1) a data-plane span layer beneath every tool call; (2) data-correctness debugging (wrong-file / stale-revision drift); (3) true latency attribution (model vs cache vs byte-fetch); (4) effect-class governance on real writes tied to the causing step; (5) real time-travel over state via OverlayDiff+snapshots+fingerprints. **The new framing adds a sixth: because mirage IS the data plane, the console can also be the live explorer of the connected sources themselves — and bridge data↔trace bidirectionally ("who touched this byte?").**
