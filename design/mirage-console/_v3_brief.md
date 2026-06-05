# Mirage Console v3 — converged brief (READ FIRST)

Third design pass. The IA has CONVERGED — do not re-litigate settled decisions; detail and combine them into a complete webpage redesign, honoring two new directives. Reference products the user loves: **Snowflake/Snowsight, Databricks, Redux DevTools.**

## Settled definition
Mirage Console = **"Snowsight for agent data access"**: a workspace-scoped, **READ-FIRST** console to interrogate what an agent actually did to real data ("model mistake vs data mistake?"). Object model, three altitudes:
- **Workspace** = persistent context (branch · TEST/LIVE) — always-visible context bar (like Snowflake role+warehouse / Databricks compute+catalog).
- **Run / Trace** = THE noun: durable, listable, permalinkable, replayable.
- **Action / VfsOp** = the atom: the observed byte (ground-truth leaf).

Three lenses fold onto a Run: **PROFILE** (Snowflake query-profile = cost/latency/IO attribution tree), **TIME-TRAVEL** (Redux = scrub action stream · stateAt(idx) · per-action diff), **LINEAGE** (Databricks = data↔trace bidirectional "who touched this").

**Home = the workspace's RUN HISTORY** (Snowflake query-history style), with the data catalog one keystroke away. Creating a run is minor; reviewing is the center of gravity.

## Reference steal-list (the one load-bearing idea each)
- **Snowsight:** query history as first-class objects + the **QUERY PROFILE** (operator tree: rows/bytes/%time/spill) + **results auto-profiling** (per-column distributions/nulls). → mirage: run history + VfsOp/step profile + data-grid column profiling.
- **Databricks:** **LINEAGE** tab on a data object (who read/wrote, up/downstream) + run **task-DAG** drill-in + persistent workspace. → mirage: path→runs/steps lineage bridge + run-spine drill-in.
- **Redux DevTools:** state = fold over actions; **TIME-TRAVEL** (jump/skip); per-action **DIFF**; **import/export** a session. → mirage: stateAt(idx), scrub, exact diff, .mirage-session export.

## NEW DIRECTIVE 1 — intent+command as a pair (the run-inspection grain)
The primary display unit when inspecting a run is an **INTENT+COMMAND card**: the operative reasoning ("why", e.g. *"read the live checkout dashboard to correlate the deploy"*) paired with the **command** it produced (`cat /s3/dashboards/checkout.json`) and that command's **observed effect** (the VfsOp leaf: bytes·source·cache·fingerprint + exit). Verbatim reasoning + full stdout are one click away (progressive disclosure). This makes each action self-explaining and powers the **INTENT≠EFFECT** flag (stated intent vs observed op). Nuance: a step can emit several commands, so the grain is `Step(intent) → [ToolCall(command) → VfsOps]` — a collapsible card, not a rigid 1:1. HONESTY: intent is ground truth only if mirage hosts the agent (cognition plane); today reasoning is **self-reported** via AG-UI THINKING (partial) — label it, and design the card to upgrade cleanly when a model gateway lands.

## NEW DIRECTIVE 2 — Snowflake-style workspace DATA VIEW
A first-class surface where a human VISUALIZES the workspace's data, Snowsight-grade. Browse the mounted sources (VFS catalog) and, per path/file/table: a rich visual preview — **schema/columns grid** for tabular, a **DATA GRID with column profiling** (distribution sparkline, null %, distinct, min/max, top values), file/blob content, type-aware renders (channels/dashboards) — plus **metadata** (fingerprint/revision/size/consistency/mode/effect-class) and a **LINEAGE "touched by N runs/steps"** panel. Catalog + results-profiling combined. HONESTY: shipped demo sources are `Fake*Resource(DiskResource)` browsed via `ls`/`cat` (`schema.json`/`data.jsonl`/`stats.json`); **no live SQL** (catalog-proxy/query.json are NotImplementedError) → disabled query bar + "derived from files / column profile computed client-side" notes; fingerprint/revision real only on S3-like sources.

## DIRECTIVE 3 — redesign the WHOLE webpage
One coherent product: the shell/context-bar; **Home** (run history + data-catalog entry); **Run view** (intent+command pairs + Profile/Time-Travel/Lineage lenses + inspector); **Data view** (above); **Compare** (two runs); **Investigation** (saved-findings notebook); **Cmd-K**. One consistent visual system (dark, dense, keyboard-first).

## REAL data we can build on TODAY (post Phase-0 slice — verified, working, tested)
- `GET /api/sessions/{id}/replay?cursor=&run_id=` → ordered **actions[]** (VfsOp: op·path·source·bytes·duration_ms·mount_prefix·fingerprint·revision·is_cache·tool_call_id·run_id) + **stateAt(idx) fold** (overlay · reads_so_far · cursor_op · diff). Deterministic, persisted, survives restart.
- VfsOp leaf is **fully stamped at emission** now: tool_call_id correlates op→toolcall→step→run; source/duration/fingerprint/revision restored.
- Store read-path: `get_vfs_ops/get_runs/get_steps/get_tool_calls` by session/run; `listSessions`; `getSessionTrace` (full AG-UI replay → reasoning/messages/tool calls). Workspace→session persistence fixed (history survives switches).
- **Touched-by** join: filter vfs_ops by mount_prefix+path → exact data→trace bridge.
- Data sources: mounts (prefix/resource/mode/effect_class) via `_console_mounts_detail`; `vfsList`/`vfsFile` (ls/cat); `schema.json`/`data.jsonl`/`stats.json` for fake tables. Reusable components: RunTracePanel/StepCard/ToolCallRow/ReasoningBlock, OverlayDiff, TrajectoryPage, EffectClassTag/CaptureBadge/mountColor, BranchTree, the existing ScoreCardDashboard primitives.
- ASPIRATIONAL (reserve, label "not yet"): hosted-intent cognition plane, latency-phase/token-cost (Span tree is a demo), lineage graph, policy/PII, live SQL.

## Honesty rules (carry through, visually)
Solid = ground truth (VfsOp leaf, exact diff, mount_prefix+path join, stateAt fold). Muted = inferred/derived (op→step pre-stamp, timestamp merge, derived cache, self-reported intent, client-computed column profiles). Dimmed = not-yet-emitted (hosted intent, lineage graph, live SQL, policy/PII). Never fake.
