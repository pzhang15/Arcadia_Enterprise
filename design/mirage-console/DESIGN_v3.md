# Mirage Console — v3 Design Doc (whole webpage)

> **Snowsight for agent data access — open a run, scrub the bytes, answer "model mistake or data mistake?" in one glance.**

**North star.** A workspace-scoped, read-first console where reviewing what an agent did to real data beats re-running it. One persistent shell never changes shape; the center swaps exactly one object — a Run or a Data object — and a single shared selection store keeps both worlds cross-lit so the model-vs-data pivot is a glance, not a navigation. Every pixel obeys a hard honesty boundary: solid = the observed byte from /replay, muted = derived, dimmed = not-yet-emitted. Never fake.

---
## How to view
High-fidelity mockup of the whole site: **`console-v3.html`** (open directly, or via the `mockup` launch config at `localhost:4178/console-v3.html`). Figures Fig 00–09 below.

## Screen index
| Fig | Screen | Backed by |
|----|--------|-----------|
| 00 | Overview | — |
| 01 | Home — Run History | listSessions + per-run rollups from get_runs/get_steps/get_tool_calls/get_vfs_ops (SOLID c |
| 02 | Run · Time-Travel lens (default landing) | getReplay(sessionId, cursor, run_id) → full actions[] (ReplayAction, 13 fields, SOLID) + s |
| 03 | Run · Profile lens | Tree shape + per-op bytes/source/duration_ms from get_vfs_ops/actions[] (SOLID). %-of-run  |
| 04 | Run · Lineage lens | Client-side join of get_vfs_ops by mount_prefix+path (no /api/lineage). Leaves SOLID; is_c |
| 05 | Data · Table skin (/database/users) | vfsList (catalog), vfsFile→schema.json/stats.json/data.jsonl. stats.json SOLID; column pro |
| 06 | Data · File-tree skin (s3 / slack / github) | vfsList (tree), vfsFile (cat→content/size). fingerprint/revision SOLID only on S3-like (.m |
| 07 | Compare two runs | Two getReplay + getSessionTrace loads; client diff over the two actions[] (SOLID). Intent  |
| 08 | Investigation — saved findings | investigationStore + /api/investigations (listInvestigations/upsertInvestigationApi/delete |
| 09 | Cmd-K — command palette | Indexes listSessions (id/intent), _console_mounts_detail+vfsList (paths/tables), loaded ac |

---

# Mirage Console — Final Whole-Webpage Design (v3, converged)

## 0. The synthesis decision (and why)

The IA has converged across three full designs and three independent judges. The verdicts are not a coin-flip on *what to build* — they are unanimous on *how to combine the three*. I am taking that mandate literally.

**The spine = Snowsight Console.** One persistent three-region shell that never changes shape: a 44px context bar, a 300px LEFT rail holding **two trees** (Run History on top, Data Catalog on the bottom), and a fluid center that renders exactly **one object** — a Run or a Data object. No dockable-pane manager (Workbench's UX is the wrong fit and the most expensive to build, per all three judges). No separate `/data` vs `/runs` routes (Trace Debugger's routing turns the model-vs-data pivot into a context switch instead of a glance — judge 1's decisive critique). The object-swap-in-one-canvas is the whole product.

**The run-view content = Trace Debugger.** Inside the center, a Run renders as the four-region debugger organism: LEFT timeline spine of intent+command cards · CENTER lens-stage with a `[PROFILE · TIME-TRAVEL · LINEAGE]` segmented control over **one shared cursor** · RIGHT docked inspector with the **causality-crumb header + permanent selected-op anchor chip** · BOTTOM transport. Default lens = **TIME-TRAVEL at cursor = last**, DIFF tab open (the correct Redux mental model: land on final state, scrub backward).

**The nervous system = Workbench.** Underneath, a single cross-filter selection store `{ workspaceId, branch, runId, opIdx, path }` (built on the shipped `consoleStore` / `sessionRunStore` pattern). Setting `opIdx` anywhere folds `stateAt(idx)` **client-side** and ripples to the center, the inspector, the rail highlight, and the transport. This upgrades the "shared `?cursor`" permalink from a string into a live nervous system and directly defuses Snowsight Console's own top risk ("reads as two apps"). The Workbench's freely-dockable grid is **rejected**; its one genuinely-superior interaction — **split two lenses over one cursor** (`⌘\`) — survives as a hidden, opt-in power-user affordance.

**The Data View = Snowsight Console's table skin, with Trace Debugger's lineage-panel grain.** Judges 2 and 3 split the Data View hair-fine; I take Snowsight Console's table-skin honesty details (static-FK label, `—`-not-zero ReservedMetadataStrip, client-profile captions) and Trace Debugger's exact touched-by ASCII (group by run → tool_call leaf, op/source facets, hop-2 co-touched line, "this workspace's loaded runs, not provenance" footer, dimmed `[graph ⤢]`).

**Hard wiring invariants (stated by judges 2 and 3, verified against the code):**
1. All inspection/correlation binds to `/replay` (`getReplay`) + `getSessionTrace` — **never** the live `useAgentStream` reducer. *Verified:* the live `VfsOp` type in `frontends/platform/src/types/agui.ts` (lines 160–168) carries only `op·path·source·bytes·mount_prefix·duration_ms·timestamp` — it lacks `tool_call_id`, `fingerprint`, `revision`, `is_cache`. `ReplayAction` in `types/replay.ts` carries all thirteen. Binding the correlation chain to the live stream would silently corrupt every cross-link and diff.
2. Fetch `/replay` once per run (it returns the full `actions[]`), then re-fold `stateAt(idx)` **client-side** on every cursor move; only re-request on run change. The server `_fold_replay_state` is pure, so the client re-fold is provably identical. This is the mitigation for the scrub fetch-storm.
3. The touched-by join is **client-side** (no `/api/lineage` exists). Every lineage panel reads **"in THIS workspace's loaded runs — not an all-history index"** plus a "load more runs to widen" affordance.

Net: **Snowsight learnability + Redux inspector clarity + Workbench cross-filter wiring — minus the dock-manager cost and the route-induced context switches.** The model-vs-data verdict in seconds.

---

## 1. Object model & altitudes (settled, restated)

Three altitudes, one context:

- **Workspace** — persistent context (`branch · TEST/LIVE`). Always-visible in the context bar; scopes every surface. Switching workspace re-roots Home, the catalog, and the open object. Backed by `listConsoleWorkspaces` / `getConsoleWorkspace`; persistence survives switches (`consoleStore.sessionByWorkspace`).
- **Run / Trace** — THE noun. Durable, listable, permalinkable, replayable. Opened from Run History; rendered as the debugger organism. Backed by `listSessions` + `getReplay` + `getSessionTrace` + `get_runs/get_steps/get_tool_calls/get_vfs_ops`.
- **Action / VfsOp** — the atom: the observed byte, the ground-truth leaf. The `ReplayAction` (13 fields). This is what `opIdx` points at.

Three **lenses** fold onto a Run over one shared cursor:
- **PROFILE** — Snowflake Query Profile: operator tree (Step→ToolCall→VfsOp waterfall) + Most-Expensive-Ops rail + IO attribution.
- **TIME-TRAVEL** — Redux DevTools: scrub `actions[]`, `stateAt(idx)` fold, per-action DIFF, skip-what-if, export.
- **LINEAGE** — Databricks: data↔trace bidirectional "who touched this," rendered from the run side.

**Home = the workspace's RUN HISTORY**, data catalog one keystroke away (it's the bottom tree of the rail, always present).

---

## 2. The shell (persistent, never unmounts)

A single-page app, dark/dense/keyboard-first. Three fixed bands wrap a center that swaps exactly one object. The shell holds the selection store, so the cursor/selection survives every object swap.

### 2.1 Top Context Bar (44px, full width, always visible)
The Snowflake role+warehouse / Databricks compute+catalog analog. Left→right:
- `◆ Mirage` glyph (→ Home).
- **Workspace dropdown** — active workspace name (e.g. `northhill_corp`). The dropdown lists workspaces from `consoleStore`; selecting re-roots everything.
- **Branch chip** — `● TEST` (amber-outline) or `● LIVE` (dimmed-solid red ring, reusing `--color-live`). Quiet. **Promote TEST→LIVE is NOT a button here** — it lives only in Cmd-K. Governance deliberately demoted to a chip + a keystroke.
- **Breadcrumb of the current object** — reflects the shared selection: `Runs / run_a1f8 / TIME-TRAVEL @ idx 14` or `Data / database / users / Data`.
- (center→right) **Cmd-K pill** (`⌘K`), a **Home glyph**, a small **connection dot**.

The bar scopes Home, Run, Data, Compare, Investigation identically.

### 2.2 Left Object Browser (300px, resizable, surface-0 — the spine)
One scrollable column, two collapsible trees with sticky section headers and a pinned filter field above each. This is the single place both worlds coexist, so crossing run↔data is always a glance.

- **TOP TREE — RUN HISTORY** (Home-in-the-rail; always present, even while a Data object is open). Flat, filterable, reverse-chron list from `listSessions`. Each row: `[status dot] · run id (mono, truncated) · branch chip · relative time · ⚑` (the INTENT≠EFFECT flag, amber, if it fired anywhere in the run). Sticky filter: search + quick chips (Branch · Wrote-anything · Touched-mount · Failed · ⚑Flagged).
- **BOTTOM TREE — DATA CATALOG** (the 13 real mounts from `_console_mounts_detail`, lazy-expanded via `vfsList`). `/database` wears a table glyph and expands to tables-as-dirs. Each mount row carries a derived `· N runs` touched-by rollup (client union over loaded `actions[]`, muted).

Selecting a Run row → center renders the Run. Selecting a catalog leaf → center renders the Data object. The rail's active item always mirrors the center (and the shared selection).

### 2.3 Center Work Area (fluid, surface-1)
Renders exactly one object:
- **RUN object** → the four-region debugger (§4).
- **DATA object** → type-aware TABLE or FILE-TREE skin (§5).

The center has internal sub-shells but the outer three bands never move.

### 2.4 Bottom band
Only the Run object paints the **Transport bar** (36px) here (§4.5). Home / Data / Compare / Investigation leave it empty.

### 2.5 Keyboard-first
`j/k` move the active tree; `Enter` opens; `⌘K` teleports; `1/2/3` switch lenses; `[ ]` step the cursor; `Home/End` jump to first/last action; `Space` play/pause; `⌘\` split a second lens (power-user); `⌘⇧S` pin to Investigation; `⌘⇧C` compare.

---

## 3. The cross-filter selection store (the nervous system)

A single store `{ workspaceId, branch, runId, opIdx, path }`, implemented on the shipped `useSyncExternalStore` pattern (`consoleStore.ts` / `sessionRunStore.ts`). The contract:

- **Set `runId`** (from a Run-history row or Cmd-K) → `getReplay(sessionId, last, runId)` fetches the full `actions[]` + final state **once**; `getSessionTrace(sessionId)` fetches AG-UI events for reasoning/messages/tool-call args+results. The debugger hydrates at `cursor = total − 1` (final state, scrub backward).
- **Set `opIdx`** (from an EFFECT row, the Most-Expensive-Ops rail, the action list, the transport, or a lineage row) → re-fold `stateAt(idx)` **client-side** over the already-loaded `actions[]` (port of `_fold_replay_state`). This ripples instantly: inspector swaps to that `ReplayAction` (Diff/State/Action/Trace), the operator tree rings the node, the transport playhead snaps, the breadcrumb updates, and **if a Data object is also showing the op's path, its catalog row + touched cell ring**.
- **Set `path`** (from a Data leaf, a lineage card, or `↗ Data`) → filter the loaded `actions[]` by `mount_prefix + path` and light the reverse touched-by. Opening `↗ Data` swaps the center to the Data object and scrolls/expands the catalog to that path.
- **Hover = faint cross-highlight; click = committed ring.**

The server fold is the source of truth; the client re-fold is a pure function over the same data, so they are provably identical. Play-mode is debounced. This store is what makes "one shell, not two apps" *hold*.

---

## 4. Run view — the debugger organism (Trace Debugger content on the Snowsight shell)

Opened like a query from history, **Profile-not-forward but Time-Travel-forward** (you land on the final state and scrub back — the Redux mental model that judges 1 & 3 flagged as correct and matching the server defaulting cursor to `total − 1`). Built by extending the shipped `RunTracePanel / StepCard / ToolCallRow / ReasoningBlock / OverlayDiff` — not rebuilt.

Four regions, all bound to one cursor:

### 4.1 Header strip
`run_a1f8 · ● TEST · 7 steps · 23 ops · 1.2 MB read / 12.8 KB written` · lens segmented control `[PROFILE · TIME-TRAVEL · LINEAGE]` · actions `[Export .mirage-session] [Compare] [Pin finding]`. Totals are SOLID (straight from `get_steps` / `get_vfs_ops`).

### 4.2 LEFT — the timeline / action spine (380px)
Top: grouping toggle `[By-Step ⇄ Flat]` + run summary line.
- **By-Step (default, the directive-1 grain):** the `StepCard` tree — `Step(intent)` header → expands to **INTENT+COMMAND cards** (§6). Each VfsOp leaf inside is a cursor target.
- **Flat:** a virtualized `ReplayAction` log — `[idx gutter] · op chip · path (mono, mountColor) · source dot · ±bytes · effect-class dot · muted cache chip`.
- **Shared rule:** the row at the cursor is ringed/active. Rows with `idx > cursor` render at ~45% opacity with a "not-yet-executed" left border — you *see* state grow as the playhead sweeps. A skipped action (what-if) gets strikethrough + "skipped."

### 4.3 CENTER — the lens stage (flex)
A lens segmented-control pinned top (hotkeys `1/2/3`) over the **same selected VfsOp**. Switching lens never moves the cursor.

**TIME-TRAVEL (default).** A tab strip `ACTION · STATE · DIFF` over the selected action:
- **DIFF (default):** top = the compact INTENT+COMMAND card for the cursor op's owning step; below = the exact per-action delta from `state.diff` (`ReplayDiff`). Writes render via `OverlayDiff` (`op · path · +added_bytes · mount_prefix · effect-class dot · CaptureBadge`). Reads render a read card (`source · is_cache` muted · `fingerprint · revision` SOLID **only when present**, else `— · S3-only via ETag`). Exact ground truth.
- **STATE:** the fold at idx — Overlay node (`state.overlay`, last-write-wins, via `OverlayDiff`) · Reads-so-far node (`state.reads_so_far` — rendered **"paths only — no per-read bytes"** because the store really is `string[]`) · Mounts node · a dimmed "backing snapshot — reconstruction deferred" stub.
- **ACTION:** the raw `ReplayAction` JSON (all 13 fields, SOLID) — "what exactly was this."

**PROFILE (Snowflake Query Profile).** Operator tree IS the Step→ToolCall→VfsOp waterfall (reuse `RunTracePanel`), each VfsOp node carrying `bytes · duration_ms · source · %-of-run` (= `op.duration_ms ÷ Σduration`, a thin bar, **labeled "derived"**). Center-top **Most-Expensive-Ops rail**: VfsOps ranked descending by bytes (toggle → `duration_ms`); each row `op · path · mount · bytes · dur · source`; click → cursor jumps to that idx and rings the node (the model-vs-data fast path). Selecting a node → leaf detail + INTENT+COMMAND card. **Honesty:** tree shape + per-op bytes/source/dur are SOLID; the latency-phase split (model/cache/fetch) is a DIMMED reserved slot ("not emitted — Span tree is a demo"); no phantom cache-hit nodes (cache reads emit no op).

**LINEAGE (Databricks, VfsOp→data direction).** Center shows the selected op's data-object header (`path · mount · effect-class`) + `[↗ open in Data]`. Below, the reverse touched-by list (same component as the Data View, §5.5), scoped to this workspace's loaded runs, with a hop-2 "co-touched in these runs" line and a dimmed `[graph ⤢]` preview labeled "op-level, not provenance."

### 4.4 RIGHT — docked inspector (400px, always visible) — the Trace Debugger graft
**Header = the causality crumb (Redux "dispatched from"), with the permanent selected-op anchor chip** — the single graft that neutralizes the lens-disorientation risk for free (judges 1, 2, 3 all called for it):

```
┌ OP /s3/dashboards/checkout_2023.json ── #14 ──────┐  ← ANCHOR CHIP (never changes across lenses)
│ dispatched from:                                   │
│   run_a1f8 › step-3 "correlate the deploy"         │  ← each segment clickable (re-cursors)
│     › tool_call tc-9e… › this op                   │
├────────────────────────────────────────────────────┤
│ read · s3 · 4.2 KB · 41 ms              (solid)     │
│ fingerprint a91f… · revision R3         (solid, s3) │
│ is_cache: yes   ⓘ derived (source==ram)            │
│ ── INTENT+COMMAND (this op) ── (the §6 card, full) │
│ ── Data object ──── [open in Data ↗] ──            │
│ ── Touched by (this workspace) ── (reverse join)   │
└────────────────────────────────────────────────────┘
```
A `⌘⇧S` pin button adds `{op, cursor permalink, note}` to Investigation.

### 4.5 BOTTOM — the transport (36px, full width)
A density mini-map of `actions[]` (bar height = bytes, color = mountColor, writes get a darker cap) with a draggable playhead bound to the shared cursor. Controls: `⏮ ◀ ▶/⏸ ▶ ⏭` · `1× / 2× / 4×`. Right: `cursor #15 of 27 · idx 14 · 12:04:07.214` (from `cursor_op.timestamp`) + `[⤓ Export .mirage-session]`. When a skip-what-if is active, a banner spans the inspector: "Hypothetical: action 9 skipped — state re-folded. [Revert]". Skip is enabled only for overlay/reads-recomputable ops; backing-FS-dependent ops show a disabled tooltip. Export = `actions[]` + `getSessionTrace` events + mount manifest (generalize `TrajectoryPage.exportJson`); import re-folds client-side, labeled "scrub limited to overlay/reads/run; backing pinned at stand-up."

### 4.6 Power-user opt-in: split lens (`⌘\`)
The one Workbench idea worth keeping. `⌘\` splits the lens stage and lets you pick a second lens over the **same cursor** — e.g. PROFILE beside TIME-TRAVEL: scrub on the left, watch Most-Expensive-Ops re-rank on the right. **Hidden by default** (discoverable via Cmd-K "split lens right" and a `⌘\` hint), so newcomers never pay a dock tax.

---

## 5. Data view — Snowsight-grade (directive 2)

Same shell; the center renders a catalog-driven, type-aware object. No route change — selecting a catalog leaf in the bottom rail tree, or hitting `↗ Data` from a VfsOp, swaps the center. If arrived from a run, a `← back to run_a1f8 @ idx 14` pill pins top-left.

### 5.1 Catalog (the rail's bottom tree)
The 13 real mounts from `_console_mounts_detail`, each row: `prefix (mono, mountColor) · resource · ro/rw chip · effect-class dot (reversibility tooltip) · subtitle "browsed as table | file-tree" · · N runs (derived touched-by rollup)`. Lazy-expand via `vfsList`. `/database` → table glyph → expands to `users, invoices, subscriptions, events`.

### 5.2 Center — TABLE skin (`/database/*`)
- **Header:** table name + **STATS STRIP from `stats.json`** — e.g. `users · 500 rows · 105,590 B · updated 2026-05-15` (SOLID).
- **DISABLED query bar** pinned below (greyed, cursor `not-allowed`), tooltip: "Live query.json / catalog-proxy — schema designed, NotImplementedError." Styled as an intentional "designed, not yet wired" affordance, never a broken input.
- **Sub-tabs `[Schema · Data]`:**
  - **SCHEMA:** columns grid from `schema.json` (`name · type · nullable · PK badge`), plus a **FOREIGN-KEYS row** rendered as STATIC arrows (`account_id → subscriptions.account_id`), explicitly labeled **"declared schema, not observed dataflow"** (NOT lineage).
  - **DATA:** a virtualized `data.jsonl` grid. Each column **header** carries a mini column-profile (type glyph · null% micro-bar · distinct · 24px sparkline) and is click-to-filter. Muted banner: "Derived from data.jsonl · column profile computed client-side from N sampled rows · no live SQL."

### 5.3 Center — FILE-TREE skin (slack / s3 / github / datadog / sheets / gdocs / tickets / customers / finance / compliance / root)
Breadcrumb path bar + a `vfsFile` (cat) text-decode preview (monospace), honesty strip: "preview only · text decode · no binary / truncation beyond fetched bytes." Type-aware renders (slack channels, dashboards) are a labeled enhancement.

### 5.4 RIGHT — Column Profile (≈400px, panel 1)
For the selected column, header "computed client-side from N sampled rows" (muted). Body: null-% fill/empty bar · distinct count · min/max; **top-values list** for categoricals (`plan`, `status`, `event_type`) or a **histogram** for numeric/timestamptz (`created_at`, `last_login`, `amount`, `mrr`, `timestamp`), bars click-to-filter the grid. **Hard rule (judges 2 & 3):** table-level `stats.json` numbers render SOLID; per-column client-derived stats render MUTED — never confuse authoritative engine-ish numbers with derived ones.

### 5.5 RIGHT — Lineage "Touched by" (panel 2) — the data↔trace bridge
The `get_vfs_ops`-by-`mount_prefix+path` **client-side** join (no `/api/lineage`). Trace Debugger's exact grain:
```
┌ LINEAGE · /database/tables/users/data.jsonl ──────[graph ⤢]┐
│ Touched by 3 runs · 5 ops   [● read 4][● write 1][src: disk]│
│ ▸ run_a1f8 "join users to subscriptions"  2 ops  ◀read ◀read│  → deep-link to Run @ that idx
│   └ tc-3c…  cat …/users/data.jsonl   read · disk · 12.4 KB  │     leaf = the VfsOp (solid)
│ ▸ run_b27c "patch the roster"        1 op   ▶write          │
│   └ tc-9e…  write …/users/data.jsonl  write · +840 B        │     fingerprint/rev omitted (disk → null, not zero-filled)
│ Co-touched in these runs (hop-2): /database/tables/subscriptions/… · /s3/exports/… │
│ ⓘ Op-level lineage from observed VfsOps in THIS workspace's loaded runs.            │
│   Not a transitive provenance graph.  [load more runs to widen]                      │
└──────────────────────────────────────────────────────────────┘
```
Facets: op-type (read/write — the lineage primitive), source (s3/disk/ram), run. `is_cache` is a MUTED facet. **No** notebook/job/pipeline taxonomy (doesn't exist). Each op row → cursor-jump back into that run's debugger (stateAt idx) and ring the op. `[graph ⤢]` opens a DIMMED mini-graph (center = path, left = runs that read, right = runs that wrote), labeled "preview · op-level, not provenance."

### 5.6 RIGHT — ReservedMetadataStrip (table skin, below lineage)
`fingerprint / revision / consistency` = **"—"** (dash) on disk mounts, with an "S3-only via ETag" hint. SOLID only where the source provides them. **Never zero-filled, never fabricated** (the single best honesty detail, per judge 3).

---

## 6. The INTENT+COMMAND card (directive 1 — the run-inspection grain)

Spec'd exactly in the dedicated field. Grain = `Step(intent) → [ToolCall(command) → VfsOps]`, a collapsible card (NOT a rigid 1:1). One component, four homes: the By-Step timeline, the Time-Travel DIFF tab, the Profile node detail, the inspector. Data sourcing: INTENT = `steps.reasoning` (AG-UI THINKING); COMMAND = `tool_calls.args` + `tool_name` + `exit_code`; EFFECT = the VfsOp leaf from `/replay`; joined by the stamped `tool_call_id`. The conservative **INTENT≠EFFECT** flag and the clean-upgrade contract (muted "self-reported · AG-UI THINKING" chip → flips to solid "observed intent" with zero layout change when a cognition plane lands) are detailed in `intentCommandCard`.

---

## 7. Compare (two runs)

`⌘⇧C` on a run, or Cmd-K "Compare runs," or select-2 in the Run-history tree. Two debugger spines side by side sharing a synced step-cursor. Top diff-summary strip: `Δ ops · Δ bytes · paths touched in A-only / B-only / both · intent-text diff`. Per-step INTENT+COMMAND cards aligned by index, with INTENT≠EFFECT flags surfaced on each side. Selecting an op in A cross-highlights the same `mount_prefix+path` row in B. For "did the fix change what the agent did to the data?" Backed by two `getReplay` + `getSessionTrace` loads; the diff is a pure client function over the two `actions[]`.

---

## 8. Investigation (saved-findings notebook)

A durable, text-forward surface backed by the shipped `investigationStore` + `/api/investigations`. Left list of investigations (`InvestigationMeta`: title · severity P1–P4 · status · trigger · authority). Right notebook of pinned cards, each = an op/diff/path snapshot + a cursor **permalink back into the exact run debugger state** + a freeform note, interleavable with markdown. `⌘⇧S` "Pin to investigation" exists on any selected op/diff/path/flag. Export the notebook to a `.mirage-session` bundle. The Snowsight-permalink-as-artifact idea, made durable — a live cross-filtered debugger layout becomes a shareable bug repro.

---

## 9. Cmd-K (the universal teleporter)

A centered overlay over any object (the shell freezes behind it). Fuzzy across: **Runs** (id / intent text from `steps.reasoning`), **Paths & Mounts**, **Tables**, **Ops** ("jump to cursor N"), **Findings**, **Lens/view commands** ("switch to Profile," "split lens right," "open path /database/tables/users in Data," "Compare with…"), and **Governance** — **"Promote TEST→LIVE" lives here and nowhere else** (unanimous across all three designs). Keyboard-only; recents + suggested actions. Selecting a result sets the shared selection or runs the command.

---

## 10. Honesty system (carried through, visually — the credibility bet)

Three tiers baked into **shared primitives** (border-style + text-opacity + chip), never per-screen — so density never erodes them (Workbench's mitigation). Mapped to the real token ladder (`text-primary/secondary/muted/faint`):

- **SOLID** = ground truth: full-opacity text + crisp border. The VfsOp leaf (`ReplayAction`), the exact diff (`ReplayDiff`), the `mount_prefix+path` join, the `stateAt` fold, `tool_calls.args/exit_code`, table-level `stats.json`.
- **MUTED** = inferred/derived: a small ⓘ chip + dotted underline, ~70% opacity. `is_cache` (derived `source==ram`), op→step pre-stamp, timestamp merge, self-reported intent, client-computed column profiles.
- **DIMMED** = not-yet-emitted: ~40% opacity + hatched "not yet" ribbon, non-interactive/preview-only. Hosted-intent cognition plane, lineage graph, live SQL, latency-phase split, policy/PII.

**Non-negotiables (verified against the code):** never fake `fingerprint/revision` on disk mounts (show `—`, S3-only via ETag); render `reads_so_far` as "paths only — no per-read bytes" (the store really is `string[]`); the INTENT≠EFFECT flag is conservative and **silent when intent is absent**; every touched-by panel says "this workspace's loaded runs, not an all-history index"; the disabled query bar carries the explicit NotImplementedError tooltip; inspection binds to `/replay` + `getSessionTrace`, never the lossy live reducer.

---

## 11. Endpoint map (every surface → a real return, or labeled aspirational)

| Surface | Real endpoint / store | Honesty |
|---|---|---|
| Context bar (workspace/branch) | `listConsoleWorkspaces`, `getConsoleWorkspace` | solid |
| Run-history tree + Home grid | `listSessions` + per-run rollups (`get_runs/get_steps/get_tool_calls/get_vfs_ops`) | counts solid; intent-preview muted |
| Data-catalog tree | `_console_mounts_detail`, `vfsList` | solid; touched-by rollup muted |
| Run debugger (all 4 regions) | `getReplay(sessionId, cursor, runId)` (full `actions[]` + `stateAt` fold) + `getSessionTrace` | solid; %-of-run + is_cache muted; latency phases dimmed |
| Client re-fold on scrub | port of `_fold_replay_state` over loaded `actions[]` | solid (pure, identical to server) |
| INTENT+COMMAND card | `steps.reasoning` (THINKING) + `tool_calls.args/exit_code/result` + VfsOp leaf, joined by `tool_call_id` | command/effect solid; intent muted; flag = solid amber heuristic |
| Data View — table skin | `schema.json` / `data.jsonl` / `stats.json` via `vfsFile` | stats.json solid; column profile muted; FK static-labeled |
| Data View — file skin | `vfsFile` (cat) | preview solid, text-decode caveat |
| Touched-by lineage (both directions) | client join of `get_vfs_ops` by `mount_prefix+path` | solid leaves; "loaded runs not provenance" footer; graph dimmed |
| Compare | two `getReplay` + `getSessionTrace`; client diff | solid |
| Investigation | `investigationStore` + `/api/investigations` | solid |
| Export/Import .mirage-session | `actions[]` + `getSessionTrace` + mount manifest (generalize `TrajectoryPage.exportJson`) | solid; "scrub limited to overlay/reads/run" |
| Promote TEST→LIVE (Cmd-K only) | `setWorkspaceMode` / `promoteEffects` | governance, demoted |
| **Aspirational (reserved, dimmed)** | hosted-intent cognition plane · latency-phase/token cost · lineage provenance graph · policy/PII · live SQL (catalog-proxy/query.json = NotImplementedError) | dimmed "not yet," slots reserved for zero-layout-change upgrade |

---

## 12. Build leverage & risks defused

**Reuse:** `RunTracePanel / StepCard / ToolCallRow / ReasoningBlock` (timeline + cards), `OverlayDiff` (Diff/State), `EffectClassTag / CaptureBadge / mountColor` (chips), `useSyncExternalStore` stores (`consoleStore / sessionRunStore / investigationStore`), `getReplay / getSessionTrace / vfsList / vfsFile / listSessions` (all shipped). The shell is a single center-swap (cheaper than the Workbench's dock grid and the Trace Debugger's full router).

**Top risks → mitigations:** (1) *"reads as two apps"* → the cross-filter store + bidirectional cross-links + the persistent rail make the pivot a glance. (2) *Lens disorientation* → the permanent anchor chip + one-time coach-mark. (3) *Touched-by overclaim* → the load-bearing "loaded runs, not provenance" footer + "load more runs" affordance on every panel. (4) *Scrub fetch-storm* → fetch once, fold client-side. (5) *Live-stream lossiness* → bind inspection to `/replay`+`getSessionTrace` only. (6) *Honesty tiers blur under density* → shared primitives, not per-screen. (7) *INTENT≠EFFECT false positives* → conservative triggers, silent on absent intent, "possible mismatch — heuristic, not a verdict." (8) *Worksheet metaphor leak* → unmistakably inert query bar with NotImplementedError tooltip.

---

## 13. Rollout (4 phases — see rolloutPhases)

Ship the shell + Home + read-only Run debugger first (everything backed by `/replay`), then the Data View, then cross-links + Compare/Investigation, then the opt-in split-lens + reserved-slot upgrades. Each phase is independently demoable and honest about what's not yet wired.

---
## Appendix A — The intent+command card (run-inspection grain)

THE INTENT+COMMAND CARD — the run-inspection grain (directive 1). One component, four homes: the By-Step timeline (left spine), the Time-Travel DIFF tab (center), the Profile node detail (center), and the inspector (right). Grain = Step(intent) → [ToolCall(command) → VfsOps] — a COLLAPSIBLE card, NOT a rigid 1:1, because one step can emit several commands.

DATA SOURCING (all real, via the stamped chain):
• INTENT = steps.reasoning, folded from AG-UI THINKING (getSessionTrace).
• COMMAND = tool_calls.args + tool_name + exit_code (the exec string).
• EFFECT = the VfsOp leaf from /replay (ReplayAction: op·path·source·bytes·is_cache·fingerprint·revision) — joined to the command by the stamped tool_call_id.
• Verbatim reasoning + full stdout come from getSessionTrace, revealed on demand.

COLLAPSED CARD (default — three tiers visible, no crowding):
┌─ Step 3 · ● correlate-the-deploy · 1.2s · 2 cmds ──────────────────────┐
│ INTENT  ⓘ self-reported · AG-UI THINKING            [muted, dotted UL] │  ← steps.reasoning, 2-line clamp
│   "read the live checkout dashboard to correlate the deploy"           │     (if empty → muted italic "No stated intent for this step")
├────────────────────────────────────────────────────────────────────────┤
│ ▾ COMMAND  $ cat /s3/dashboards/checkout.json          exit 0 · 6ms     │  ← tool_calls.args + exit_code (SOLID)
│     └ EFFECT  read · /s3/dashboards/checkout_2023.json                  │  ← the VfsOp leaf (SOLID); click → cursor jumps to its idx + rings everywhere
│              s3 · 4.2 KB · rev R3 · etag a91f · [cache]                 │     fingerprint/rev SOLID only when present (S3-like); [cache] chip MUTED (derived source==ram)
│     ⚑ INTENT≠EFFECT — "live" intent vs cached read of a 2023 path       │  ← SOLID amber flag (conservative heuristic)
│ ▸ COMMAND  $ jq '.errors' …                            exit 0 · 2ms     │  ← 2nd command, independently collapsible (proves the Step→[cmds] grain)
└────────────────────────────────────────────────────────────────────────┘

PROGRESSIVE DISCLOSURE (three tiers, one click each):
1. (default) intent line + command + one-line effect.
2. "▸ verbatim" under INTENT → expands full steps.reasoning (THINKING fold); "▸ full stdout" on a COMMAND → expands tool_calls.result (reuse ToolCallRow's pre block).
3. clicking the EFFECT row → sets shared opIdx → time-travels the cursor to that exact VfsOp and opens its DIFF (rings the operator-tree node, snaps the transport, lights any open Data object's path).

THE INTENT≠EFFECT FLAG (the model-vs-data fast path, the single highest-value pixel):
• A CONSERVATIVE client heuristic comparing self-reported intent text vs the observed op. Fires ONLY when intent exists AND contradicts the op — e.g. reasoning contains live/latest/current/production but is_cache==true; or names path A but the VfsOp read path B; or "production" vs a path containing "2023"/"staging".
• Rendered as a SOLID amber inline chip (the comparison's right-hand side — the effect — IS observed truth) with a muted explainer. Tooltip: "possible mismatch — heuristic over self-reported intent vs observed op, not a semantic verdict."
• NEVER fires when intent is absent (no claim → no contradiction). User can dismiss/mark-as-wrong (feeds nothing today, but honest).
• Reading it: mismatch → suspect a MODEL mistake (intent wrong). Intent matches but the bytes/source/freshness are wrong → a DATA mistake → pivot via [open in Data ↗] to inspect fingerprint/revision. Also surfaced as a ⚑ column on the Home run table so triage starts before you open a run.

INTENT≠EFFECT vs HONESTY (the clean-upgrade contract):
• The INTENT row is the MUTED tier (dotted underline + "self-reported · AG-UI THINKING" ⓘ chip) because today's system prompt only says the agent "may show your reasoning." When steps.reasoning is empty it degrades to "No stated intent for this step" (muted italic) — never fabricated, never LLM-summarized.
• The chip RESERVES the exact slot to flip to a SOLID "observed intent" chip with ZERO layout change when a hosted cognition plane (model gateway) lands.
• COMMAND and EFFECT rows are ALWAYS SOLID (observed I/O). The flag sits between them, comparing the muted claim to the solid effect — which is precisely why it can only ever be "possible," and the card says so.

## Appendix B — The Snowflake-style data view

SNOWFLAKE-STYLE DATA VIEW (directive 2) — first-class, Snowsight-grade, rendered as the center object (no route change). Catalog + results auto-profiling + metadata + touched-by, combined. Three regions inside the center, on the persistent shell.

═══ CATALOG (the rail's bottom tree, 300px) ═══  (Snowsight Databases explorer)
Header 'Catalog · northhill_corp' + search. The 13 REAL mounts from _console_mounts_detail, lazy-expanded via vfsList. Each mount row: prefix (mono, mountColor) · resource · ro/rw chip · effect-class dot (hover = reversibility tooltip) · subtitle 'browsed as table | file-tree' · derived '· N runs' touched-by rollup (MUTED, client union over loaded actions[] by mount_prefix).
The exact 13 mounts (verified against mounts.py + effectClass.ts):
  / RAMResource rw scratch (file) · /slack ro external-effect (file) · /sheets ro durable-internal (file) · /gdocs ro durable-internal (file) · /tickets rw durable-internal (file) · /github ro external-effect (file) · /pagerduty ro external-effect (file) · /datadog ro durable-internal (file) · /finance ro system-of-record (file) · /customers ro system-of-record (file) · /compliance ro durable-internal (file) · /database ro durable-internal (TABLE glyph → users/invoices/subscriptions/events) · /s3 ro durable-internal (file).

═══ CENTER — TYPE-AWARE DETAIL ═══
TABLE SKIN (/database/{users,invoices,subscriptions,events}):
• HEADER = table name + STATS STRIP from stats.json (SOLID): users 500 rows / 105,590 B / updated 2026-05-15T12:00:00Z · invoices 200 / 29,266 B · subscriptions 51 / 8,844 B · events 5,000 / 762,545 B / 2026-05-15T14:30:00Z.
• DISABLED QUERY BAR pinned below (greyed, cursor not-allowed) — tooltip 'Live query.json / catalog-proxy — schema designed, NotImplementedError.' Styled as an intentional 'designed, not yet wired' affordance.
• SUB-TABS [Schema · Data]:
  – SCHEMA = columns grid from schema.json [name · type · nullable · PK badge] + a FOREIGN-KEYS row rendered as STATIC arrows, labeled 'declared schema, not observed dataflow' (NOT lineage). Real FKs: users.account_id → subscriptions.account_id; invoices.account_id → subscriptions.account_id; subscriptions.account_id → customers.account_id; events.user_id → users.user_id.
  – DATA = virtualized data.jsonl grid. Each column HEADER carries a mini column-profile (type glyph · null% micro-bar · distinct · 24px sparkline) + click-to-filter. Muted banner 'Derived from data.jsonl · column profile computed client-side from N sampled rows · no live SQL.'
FILE-TREE SKIN (all other mounts): breadcrumb + vfsFile (cat) text-decode preview (monospace) + honesty strip 'preview only · text decode · no binary / truncation beyond fetched bytes.'

═══ RIGHT — TWO STACKED PANELS (≈400px) + a strip ═══
PANEL 1 — COLUMN PROFILE (Snowsight results auto-profiling), for the selected column. Header 'computed client-side from N sampled rows' (MUTED). Body: null-% fill/empty bar · distinct count · min/max; TOP-VALUES list for categoricals (plan/status/event_type) or a HISTOGRAM for numeric/timestamptz (created_at/last_login/amount/mrr/timestamp/start_date/renewal_date), bars click-to-filter the grid. ALL computed from data.jsonl (stats.json is table-level only — no per-column distributions on disk) and labeled MUTED.
HARD RULE (judges 2 & 3): table-level stats.json renders SOLID; per-column client-derived stats render MUTED — never confuse authoritative engine-ish numbers with derived ones.
Example column profiles (real values): users.plan top-values free/business/enterprise; users.status active/inactive; users.last_login histogram (~6% null bar); invoices.status paid/overdue/pending; invoices.amount histogram (numeric12,2); subscriptions.mrr histogram (e.g. 40000, 8000); subscriptions.plan enterprise/business; events.event_type top-values (webhook_trigger…); events.timestamp histogram.

PANEL 2 — LINEAGE 'Touched by' (Databricks lineage-on-the-object), the data→runs direction (the data↔trace bridge):
┌ LINEAGE · /database/tables/users/data.jsonl ───────────────────[graph ⤢]┐
│ Touched by 3 runs · 5 ops          [● read 4][● write 1][src: disk]      │  ← op-type + source facets (real)
│ ▸ run_a1f8c2 "join users to subscriptions"   2 ops   ◀read ◀read          │  ← group by run_id → deep-link to Run @ that idx
│   └ tc-3c…  cat …/users/data.jsonl   read · disk · 103 KB                  │     leaf = the VfsOp (SOLID)
│ ▸ run_b27c91 "patch the user roster"         1 op    ▶write                │
│   └ tc-9e…  write …/users/data.jsonl write · +840 B                        │     fingerprint/rev omitted (disk → null, NOT zero-filled)
│ Co-touched in these runs (hop-2): /database/tables/subscriptions/… · /s3/… │  ← honest 2-hop co-occurrence, NOT directional/downstream
│ ⓘ Op-level lineage from observed VfsOps in THIS workspace's loaded runs.   │
│   Not a transitive provenance graph.   [load more runs to widen]           │
└────────────────────────────────────────────────────────────────────────────┘
Facets: op-type (read/write — the lineage primitive), source (s3/disk/ram), run. is_cache = a MUTED facet. NO notebook/job/pipeline taxonomy (doesn't exist). Each op row → cursor-jump back into that run's debugger (stateAt idx) and ring the op. [graph ⤢] = a DIMMED mini-graph preview (center=path, left=runs that read, right=runs that wrote, hop-2 paths as faint satellites), labeled 'preview · op-level, not provenance.'

STRIP (table skin only, below lineage) — RESERVED METADATA: fingerprint / revision / consistency = '—' (dash) on disk mounts ('S3-only via ETag'), SOLID only where the source provides them (e.g. /s3/.../revenue.csv → etag-7c41a9 / R12). NEVER fabricated, NEVER zero-filled.

JOIN IMPLEMENTATION NOTE (honesty, verified against code): there is NO /api/lineage and NO server path filter — the touched-by join is CLIENT-SIDE, computed by unioning each loaded run's actions[] (from getReplay/get_vfs_ops) and filtering by mount_prefix+path. 'Touched by N runs' = N runs LOADED in this workspace, not an all-history cross-workspace index (stated in the footer on every panel).

CROSS-FILTER: when the shared opIdx points at a path this table/file is showing, the catalog row + (table) the touched cell ring; selecting a column/row here stays local (data inspection), but selecting a lineage row drives the global selection (→ the run debugger).

## Appendix C — Information architecture

ONE persistent single-page shell that never unmounts; the CENTER swaps exactly one object (Run or Data). No app-level routing beyond which object the center shows + permalink params. No dockable-pane manager. No separate /data vs /runs routes.

SHELL (3 fixed bands, always-on):
- TOP CONTEXT BAR (44px): ◆Mirage · Workspace dropdown · branch chip ●TEST/●LIVE (promote is Cmd-K-only) · breadcrumb of current object · Cmd-K pill · Home glyph · connection dot. Scopes every surface.
- LEFT OBJECT BROWSER (300px, surface-0, the spine): ONE scrollable column, TWO collapsible trees w/ sticky headers + per-tree filter field. TOP = RUN HISTORY (Home-in-the-rail, always present). BOTTOM = DATA CATALOG (13 mounts, lazy vfsList; /database → tables). Selecting a run row → Run object; selecting a catalog leaf → Data object. Active item mirrors the center + shared selection.
- BOTTOM band: only the Run object paints the Transport bar here.

CENTER (fluid, surface-1): renders ONE object —
  • RUN = 4-region debugger: LEFT timeline spine (intent+command cards / flat action log) · CENTER lens stage [PROFILE·TIME-TRAVEL·LINEAGE] over ONE shared cursor · RIGHT docked inspector (causality crumb + permanent selected-op anchor chip) · BOTTOM transport. Default lens TIME-TRAVEL @ cursor=last, DIFF tab.
  • DATA = type-aware: TABLE skin (database tables) or FILE-TREE skin (everything else): LEFT catalog (the rail tree) · CENTER table/file detail · RIGHT column-profile + touched-by lineage + reserved-metadata strip.

NERVOUS SYSTEM: one selection store {workspaceId, branch, runId, opIdx, path} on the shipped useSyncExternalStore pattern. Set opIdx anywhere → client-side stateAt(idx) re-fold (port _fold_replay_state; fetch /replay once per run) → ripples to center, inspector, rail highlight, transport, and any open Data object showing that path. Set path → filter actions[] by mount_prefix+path, light reverse touched-by. Hover=faint, click=committed ring.

PERMALINKS (params on the SPA, not separate routes): workspace, branch, runId, opIdx (cursor), lens, path, col, docks(split). Browser back/forward = history of object selections; the rail selection always reflects the center.

SURFACES: Shell+ContextBar · Home(run history + catalog peek) · Run debugger(3 lenses + inspector + transport) · Data view(table+file skins) · Compare(two runs) · Investigation(saved findings) · Cmd-K(global overlay). One dark/dense/keyboard-first visual system reusing the shipped token ladder.

WIRING INVARIANTS (verified against code): inspection binds to /replay + getSessionTrace, NEVER the live useAgentStream reducer (its VfsOp lacks tool_call_id/fingerprint/revision/is_cache); touched-by is a client-side mount_prefix+path union over THIS workspace's loaded runs (no /api/lineage); honesty tiers solid/muted/dimmed are shared primitives.

## Appendix D — Build-ready screen specs

### Fig 01 · Home — Run History

**Purpose.** The workspace's gravity well: scan what agents did to our data lately and open a run, with the data catalog one keystroke away. Reviewing > running.

**Layout.** Context bar on top. LEFT rail (300px): RUN HISTORY tree (top, active) + DATA CATALOG tree (bottom, collapsed to mount roots). CENTER (cold open, no object selected): a full-width virtualized run-history GRID. Band 1 = header strip (h1 'Runs' · count · de-emphasized [+ New run] · view toggle [List ▢ | Matrix ▦]). Band 2 = sticky filter bar (chips: Branch All/TEST/LIVE · Status ok/error/running · ☑ Wrote-anything · Touched-mount ▾ · ⚑ Flagged · free-text). Band 3 = the columnar grid. A 280px collapsible MINI-CATALOG PEEK pins right ('Data catalog →' with the 13 mounts + touched-by rollups). No transport band (no run open yet).

**Key components.** Run-history virtualized grid · Filter chip bar (maps to real fields) · Status dot + branch chip + ⚑ INTENT≠EFFECT column · Mini-catalog peek (13 mounts + derived 'N runs' rollups) · List⇄Matrix toggle · Row quick-actions (Open/Compare/Export/⋯) · EmptyState

**Sample data.** Count: '37 runs · northhill_corp · branch TEST'. Grid columns [● status | RUN | INTENT PREVIEW (muted) | BRANCH | STEPS | OPS | BYTES | WROTE | ⚑ | STARTED | DURATION]. Rows:
● run_a1f8c2 · 'correlate the deploy with the live checkout dashboard' · TEST · 7 · 23 · 1.2 MB · ▲2 (s3·tickets dots) · ⚑ · 12m ago · 8.4s
● run_b27c91 · 'patch the user roster for ACCT-2039' · TEST · 4 · 11 · 384 KB · ▲1 (database dot) · — · 41m ago · 3.1s
● run_4e0d77 · 'reconcile invoices against subscriptions' · TEST · 9 · 31 · 2.0 MB · — · — · 1h ago · 11.7s
◐ run_9ac3f0 · 'audit overdue invoices' · LIVE · 6 · 18 · 612 KB · ▲1 · — · 3h ago · 6.2s
● run_77b210 · (no stated intent for first step) · TEST · 3 · 7 · 88 KB · — · — · 5h ago · 2.0s
✕ run_d5512a · 'export Q1 revenue from /s3' · TEST · 5 · 9 · 4.2 MB · — · ⚑ · 6h ago · ERR exit 2
Mini-catalog peek: /database ro system→durable · table · 4 runs; /s3 ro durable · file · 6 runs; /slack ro external · file · 2 runs; /tickets rw durable · file · 3 runs; /finance ro system · file · 1 run. Footer: 'Counts are over runs loaded in this workspace, not an all-history index.'

**Signature.** Click any run row → the center swaps to that run's debugger (Debug landing: Time-Travel @ cursor=last, DIFF tab) without leaving the shell; the rail still shows run history so the next run is one click away. The ⚑ column lets triage start before opening a run.

**Endpoints.** listSessions + per-run rollups from get_runs/get_steps/get_tool_calls/get_vfs_ops (SOLID counts/bytes/branch). Intent-preview = first step's steps.reasoning (MUTED, self-reported). ⚑ = client INTENT≠EFFECT heuristic. Mini-catalog = _console_mounts_detail + client touched-by rollup (MUTED). 'New run' de-emphasized (creating is minor).

### Fig 02 · Run · Time-Travel lens (default landing)

**Purpose.** Scrub a run as a recording: land on final state, step backward, read the exact per-action diff, and catch model-vs-data mismatches.

**Layout.** Context bar (breadcrumb 'Runs / run_a1f8c2 / TIME-TRAVEL @ idx 14'). Header strip (id·branch·totals·[Export][Compare][Pin]) + lens segmented control. LEFT (380px) timeline spine [By-Step ⇄ Flat], By-Step default showing INTENT+COMMAND cards, rows past cursor at 45% opacity. CENTER lens stage with tab strip ACTION·STATE·DIFF (DIFF default = intent+command card on top + exact state.diff below). RIGHT (400px) docked inspector (causality crumb + anchor chip + op detail + intent+command + touched-by). BOTTOM transport (36px): bytes mini-map + playhead + ⏮◀▶⏭ + 1×/2×/4× + 'cursor #15 of 27 · idx 14 · 12:04:07.214' + [⤓ Export].

**Key components.** By-Step timeline of INTENT+COMMAND cards (StepCard) · Flat virtualized ReplayAction log · ACTION/STATE/DIFF tab strip · OverlayDiff (write) + read-card (read) · Causality-crumb inspector + selected-op anchor chip · Transport mini-map + playhead · Skip-what-if banner

**Sample data.** Header: run_a1f8c2 · ●TEST · 7 steps · 23 ops · 1.2 MB read / 0 B written. Cursor at idx 14. DIFF tab (read): kind=read · path /s3/dashboards/checkout_2023.json · source s3 · is_cache true (muted) · fingerprint a91f3c… (solid) · revision R3 (solid). Intent+command card on top: INTENT 'read the live checkout dashboard to correlate the deploy' (muted) / COMMAND $ cat /s3/dashboards/checkout.json exit 0 · 6ms / EFFECT read · /s3/dashboards/checkout_2023.json · s3 · 4.2 KB · rev R3 · etag a91f · [cache] / ⚑ INTENT≠EFFECT — 'live' vs cached read of a 2023 path. Timeline By-Step: Step 1 'list dashboards' (1 cmd, 2 ops) · Step 2 'fetch deploy log' (1 cmd, 1 op) · Step 3 'correlate the deploy' (2 cmds, 3 ops, ⚑) · Step 4 'summarize' (1 cmd, 0 ops). Transport mini-map: 23 bars, tallest at idx 9 (read /s3/.../app.log 512 KB).

**Signature.** Drag the playhead (or Space to play over real timestamps): rows past the cursor fade in to solid, the STATE overlay accretes writes, reads_so_far fills. Toggle SKIP on a read → client re-fold under a 'Hypothetical: action 9 skipped — [Revert]' banner. Clicking any EFFECT row jumps the cursor to that idx and rings it everywhere.

**Endpoints.** getReplay(sessionId, cursor, run_id) → full actions[] (ReplayAction, 13 fields, SOLID) + stateAt fold (overlay/reads_so_far(paths-only)/cursor_op/diff). getSessionTrace → reasoning/args/results. Client re-fold (port _fold_replay_state) on cursor move; refetch only on run change. is_cache MUTED.

### Fig 03 · Run · Profile lens

**Purpose.** Snowflake Query Profile for a run: rank ops by cost, find the expensive byte, attribute IO — the model-vs-data fast path.

**Layout.** Same shell + header + lens strip over the SAME cursor. CENTER: operator tree (Step→ToolCall→VfsOp waterfall) on the left of the stage with per-node bytes·dur·source·%-of-run bars (labeled 'derived'); a MOST-EXPENSIVE-OPS rail center-top (ranked by bytes, toggle→duration_ms); selected node → leaf detail + INTENT+COMMAND card. RIGHT inspector gains an IO-attribution block (bytes-by-source, cache-ratio muted, bytes-by-mount by effect-class) + a DIMMED 'latency phases — not emitted' slot. Transport still live below.

**Key components.** Operator tree (RunTracePanel) with %time bars · Most-Expensive-Ops rail (click→cursor+ring) · IO-attribution strip (bytes-by-source / cache-ratio / bytes-by-mount) · Dimmed latency-phase reserved slot · INTENT+COMMAND card on node select

**Sample data.** Most-Expensive-Ops (by bytes): 1) read /s3/northhill-data/logs/platform-api/2026/05/15/app.log · s3 · 512 KB · 41ms; 2) read /database/tables/events/data.jsonl · disk · 762 KB? (sampled) · 28ms; 3) read /s3/.../2026/05/14/app.log · s3 · 318 KB · 33ms; 4) read /database/tables/users/data.jsonl · disk · 103 KB · 12ms. IO-attribution: bytes-by-source s3 1.0 MB / disk 205 KB / ram 4.2 KB; cache-ratio 'is_cache 3 of 18 reads' (muted derived); bytes-by-mount: s3(durable) 1.0 MB · database(durable) 205 KB · tickets(durable) 0. Latency-phase slot greyed: 'model/cache/fetch split — not emitted, Span tree is a demo'.

**Signature.** Click the top Most-Expensive-Op row → the cursor flies to that op idx, the operator tree rings the node, and the transport playhead snaps. Read the top 3 rows to triage 23 ops without scrolling.

**Endpoints.** Tree shape + per-op bytes/source/duration_ms from get_vfs_ops/actions[] (SOLID). %-of-run = op.duration_ms ÷ Σduration (DERIVED, labeled). Cache-ratio = client count is_cache/reads (MUTED). Latency-phase split = DIMMED reserved (not emitted). No phantom cache-hit nodes.

### Fig 04 · Run · Lineage lens

**Purpose.** From the run side, see which data each op touched and pivot into the Data View — the data↔trace bridge, run→data direction.

**Layout.** Same shell. CENTER: the selected op's data-object header (path · mount · effect-class) + [↗ open in Data]; below, the reverse 'Touched by' list grouped by run→tool_call with op/source facets and a hop-2 co-touched line; a DIMMED [graph ⤢] preview. RIGHT inspector: selected VfsOp op·source·bytes·fingerprint/rev (S3-only) + a reverse touched-by mini-list. Transport live below.

**Key components.** Op data-object header + [↗ Data] bridge · Touched-by list (group by run→tool_call) · Op-type/source facet chips · Hop-2 co-touched line · Dimmed lineage-graph preview · Honest scope footer

**Sample data.** Selected op: /database/tables/users/data.jsonl (database · durable-internal · ro). Touched by 3 runs · 5 ops [● read 4][● write 1][src: disk]. ▸ run_a1f8c2 'join users to subscriptions' 2 ops ◀read ◀read └ tc-3c… cat …/users/data.jsonl read·disk·103 KB. ▸ run_b27c91 'patch the user roster' 1 op ▶write └ tc-9e… write …/users/data.jsonl write·+840 B (fingerprint/rev '—', disk). Hop-2: /database/tables/subscriptions/data.jsonl · /s3/northhill-data/exports/monthly/2026-04-customers.csv. Footer: 'Op-level lineage from observed VfsOps in THIS workspace's loaded runs. Not a transitive provenance graph. [load more runs to widen]'.

**Signature.** Click [↗ open in Data] → center swaps to the users table's Data object with its touched-by card lit; the back-pill '← run_a1f8c2 @ idx 14' lets you return. Click any touched-by row → cursor-jump into that run's debugger at the exact idx, op ringed.

**Endpoints.** Client-side join of get_vfs_ops by mount_prefix+path (no /api/lineage). Leaves SOLID; is_cache MUTED facet; fingerprint/rev omitted on disk; graph DIMMED preview. Scope label load-bearing.

### Fig 05 · Data · Table skin (/database/users)

**Purpose.** Snowsight-grade table view: catalog → schema → data grid with column profiling → metadata + touched-by. Visualize the workspace's data and see who touched it.

**Layout.** Same shell; center renders the TABLE object. LEFT catalog tree expanded to /database/{users,invoices,subscriptions,events}. CENTER: header (table name + STATS STRIP) + DISABLED query bar + sub-tabs [Schema · Data]. Schema = columns grid + static FK row. Data = virtualized data.jsonl grid with per-column-header mini-profiles + click-to-filter. RIGHT (400px): COLUMN PROFILE (panel 1) + LINEAGE touched-by (panel 2) + ReservedMetadataStrip (below). No transport.

**Key components.** Catalog tree (13 mounts, /database→tables) · Stats strip from stats.json (SOLID) · Disabled query bar (NotImplementedError tooltip) · Schema grid + static FK arrows (labeled) · Virtualized data.jsonl grid + per-column mini-profiles · Column-profile panel (client-side, MUTED) · Touched-by lineage panel · ReservedMetadataStrip ('—' on disk)

**Sample data.** Header: users · 500 rows · 105,590 B · updated 2026-05-15T12:00:00Z (SOLID). Disabled query bar placeholder 'SELECT … — live query (catalog-proxy NotImplementedError)'. SCHEMA grid: user_id varchar(36) NOT NULL [PK] · account_id varchar(16) NOT NULL · email varchar(255) NOT NULL · created_at timestamptz NOT NULL · last_login timestamptz NULL · plan varchar(32) NOT NULL · status varchar(16) NOT NULL. FK row (static): 'account_id → subscriptions.account_id — declared schema, not observed dataflow'. DATA grid rows: {usr_00000, ACCT-2024, arodriguez@example.org, 2024-04-25…, 2024-07-18…, free, active} · {usr_00001, ACCT-2033, shannondiaz@example.com, 2025-01-08…, 2025-03-17…, free, inactive} · {usr_00002, ACCT-2039, margarethaney@example.net, 2025-11-16…, 2026-02-19…, free, active}. Column-profile for 'plan' (top-values, MUTED, computed from 500 sampled rows): free 0.61 · business 0.22 · enterprise 0.17; for 'last_login' (histogram, null% bar shows ~6% null). ReservedMetadataStrip: fingerprint — · revision — · consistency — (S3-only via ETag). Touched by 3 runs · 5 ops.

**Signature.** Select a column header (e.g. 'plan') → the right Column-Profile panel computes null%/distinct/top-values from sampled rows; click a top-value bar to filter the grid — labeled 'computed client-side, no live SQL' so it's never mistaken for engine stats. Click a touched-by row → jump back into that run's debugger at the op.

**Endpoints.** vfsList (catalog), vfsFile→schema.json/stats.json/data.jsonl. stats.json SOLID; column profile MUTED (client-side from sampled rows); FK from schema.json rendered static; touched-by = client get_vfs_ops join; fingerprint/rev '—' (disk). Live SQL = DIMMED/disabled.

### Fig 06 · Data · File-tree skin (s3 / slack / github)

**Purpose.** Browse non-tabular mounts as a file tree with a text preview + metadata + touched-by — same honesty, same bridge.

**Layout.** Same shell; center renders the FILE object. LEFT catalog tree expanded (e.g. /s3/northhill-data/...). CENTER: breadcrumb path bar + vfsFile text-decode preview (monospace) + honesty strip. RIGHT: lightweight metadata panel (size·mode·effect-class·fp/rev) + LINEAGE touched-by card. Column-profile panel hidden (non-tabular). No transport.

**Key components.** Catalog file tree (lazy vfsList) · Breadcrumb path bar · vfsFile monospace preview + honesty strip · Metadata panel (size/mode/effect-class/fingerprint/revision) · Touched-by lineage card

**Sample data.** Path: /s3/northhill-data/exports/monthly/2026-04-revenue.csv (s3 · durable-internal · ro). Preview (text decode): 'account_id,plan,mrr,month\nACCT-1001,enterprise,40000.00,2026-04\nACCT-1002,business,8000.00,2026-04\n…'. Honesty strip: 'preview only · text decode · no binary / truncation beyond fetched bytes'. Metadata: size 18.4 KB · mode ro · effect-class durable-internal · fingerprint etag-7c41a9 (SOLID, s3) · revision R12 (SOLID, s3). Alternate (disk) example /github/repos/northhill/platform-api/README.md: fingerprint — · revision —. Touched by 2 runs · 3 ops [● read 3][src: s3].

**Signature.** Select a file → its mount_prefix+path becomes the shared selection, so the touched-by join and any open run's run-side cross-links stay in sync; S3 files show real fingerprint/revision, disk files show '—' (never zero-filled).

**Endpoints.** vfsList (tree), vfsFile (cat→content/size). fingerprint/revision SOLID only on S3-like (.meta/ETag); disk → '—'. Touched-by = client get_vfs_ops join. Type-aware renders (channels/dashboards) = labeled enhancement.

### Fig 07 · Compare two runs

**Purpose.** Answer 'did the fix change what the agent did to the data?' by diffing two runs side by side.

**Layout.** Context bar. Top diff-summary strip (Δ ops · Δ bytes · paths A-only/B-only/both · intent-text diff). Two debugger spines side by side (Run A | Run B), action streams aligned by index, sharing a synced step-cursor; per-step INTENT+COMMAND cards aligned with INTENT≠EFFECT flags surfaced; a mini-transport per side. Entry via ⌘⇧C or Cmd-K.

**Key components.** Diff-summary strip · Two aligned debugger spines · Aligned INTENT+COMMAND cards · Path/bytes/writes diff · Per-side mini-transport · INTENT≠EFFECT flags on both sides

**Sample data.** A = run_a1f8c2 (before) vs B = run_a1f8d9 (after fix). Δ ops: 23 → 19 (−4). Δ bytes read: 1.2 MB → 840 KB. Paths: A-only [/s3/dashboards/checkout_2023.json (cached, ⚑)]; B-only [/s3/dashboards/checkout.json (fresh, no ⚑)]; both [/database/tables/users/data.jsonl, /s3/.../app.log]. Intent diff on Step 3: A 'read the live checkout dashboard' → effect cached 2023 (⚑ INTENT≠EFFECT); B same intent → effect fresh checkout.json (no flag). Verdict surfaced: the fix turned a data-mistake (stale cached read) into a clean read.

**Signature.** Select an op in A → the same mount_prefix+path row cross-highlights in B (and vice-versa); the INTENT≠EFFECT flag disappearing from A→B is the visual proof the data-mistake is fixed.

**Endpoints.** Two getReplay + getSessionTrace loads; client diff over the two actions[] (SOLID). Intent diff from steps.reasoning (MUTED). Flag = client heuristic.

### Fig 08 · Investigation — saved findings

**Purpose.** Turn a live cross-filtered debugger state into a durable, shareable artifact: the Snowsight-permalink-as-finding.

**Layout.** Context bar. LEFT list of investigations (title · severity · status · trigger). RIGHT notebook of pinned cards interleavable with markdown; each card = op/diff/path snapshot + cursor permalink back into the exact run state + freeform note. Footer: [Export .mirage-session bundle]. Reached via Cmd-K or rail footer; 'Pin to investigation' (⌘⇧S) exists on any op/diff/path/flag.

**Key components.** Investigation list (InvestigationMeta) · Notebook of pinned finding cards · Cursor-permalink chips (jump back into run state) · Markdown interleave · Severity/status/trigger badges · Export bundle

**Sample data.** Investigation: 'Stale checkout dashboard reads' · P2 · needs_review · trigger alert · authority read_only. Cards: (1) ⚑ INTENT≠EFFECT @ run_a1f8c2 idx 14 — note 'agent claimed live but read /s3/.../checkout_2023.json [cache]; data-mistake, not model.' permalink ?run=a1f8c2&cursor=14&lens=timetravel. (2) DIFF @ run_a1f8c2 idx 9 — note 'largest read 512 KB app.log, fine.' (3) Markdown: '## Root cause — cache key omitted the date; fix = invalidate dashboard cache nightly.' Other investigations: 'Q1 revenue export failure' P3 escalated; 'Roster patch review' P4 resolved.

**Signature.** Click a permalink chip on a finding card → the center reconstructs that exact run debugger state (run + cursor + lens), op ringed — the bug repro travels with the note.

**Endpoints.** investigationStore + /api/investigations (listInvestigations/upsertInvestigationApi/deleteInvestigationApi). Finding snapshots reference ReplayAction idx + permalink; export bundles actions[] + getSessionTrace + mount manifest. SOLID.

### Fig 09 · Cmd-K — command palette

**Purpose.** The universal teleporter and the ONLY home for governance: jump anywhere, run any view command, promote TEST→LIVE deliberately.

**Layout.** Centered overlay over the frozen shell; single search field + grouped fuzzy results. Keyboard-only; recents + suggested actions at rest.

**Key components.** Fuzzy search across runs/paths/tables/ops/findings · Grouped results (Runs · Paths&Tables · Ops · Findings · Commands · Governance) · View/lens commands (switch lens, split lens right, open path in Data, Compare with…) · Governance: Promote TEST→LIVE (only home) · Jump-to-cursor N

**Sample data.** Query 'check' → Runs: run_a1f8c2 'correlate the deploy with the live checkout…'. Paths&Tables: /s3/dashboards/checkout.json · /s3/dashboards/checkout_2023.json · database/tables/… Ops: 'jump to cursor 14 (read checkout_2023.json)'. Commands: 'Open /database/tables/users in Data' · 'Split lens: Profile right' · 'Compare run_a1f8c2 with…' · 'Export .mirage-session'. Governance: 'Promote workspace northhill_corp TEST→LIVE' (demoted, with a confirm). Findings: 'Stale checkout dashboard reads (P2)'.

**Signature.** Type to fuzzy-match across every noun and verb; selecting a result sets the shared selection (run/op/path) or runs the command. Promote lives here and nowhere else — governance is a deliberate keystroke, never a tempting button.

**Endpoints.** Indexes listSessions (id/intent), _console_mounts_detail+vfsList (paths/tables), loaded actions[] (ops), investigationStore (findings). Promote → setWorkspaceMode/promoteEffects. Split-lens/open-in-Data drive the SPA selection.

## Appendix E — Signature interactions

- The model-vs-data pivot in one click, both directions, one shared selection: from any VfsOp EFFECT row [open in Data ↗] swaps the center to that mount_prefix+path's Data object and lights its Touched-by card; from a Touched-by row, jump straight back into that Run's Time-Travel at the exact op idx (stateAt fold) with the op ringed. Same client-side join, read two ways.
- Cross-filter select (the nervous system): clicking an EFFECT row / a Most-Expensive-Ops row / an action / a lineage row sets the shared opIdx → client-side stateAt(idx) re-fold → inspector swaps to that ReplayAction, operator tree rings the node, transport snaps, breadcrumb updates, and any open Data object showing that path rings its catalog row. Hover = faint, click = committed ring.
- Most-Expensive-Ops → cursor (Profile): click the top-ranked VfsOp by bytes and the operator tree rings it + the transport lands on its idx — triage 23 ops by reading the top three rows, Snowsight's 'find the expensive node' on a real byte spine, zero new endpoint.
- Lens switching over ONE cursor with a permanent anchor: toggling PROFILE↔TIME-TRAVEL↔LINEAGE (1/2/3) re-skins the center at the same idx; the inspector's selected-op anchor chip never changes, so you never lose the op — the cure for lens disorientation, and the permalink (?run&lens&cursor) reconstructs it exactly.
- Scrub the fold: drag the bottom mini-map playhead (or Space to play over real timestamps) and watch state GROW — past-cursor rows fade in to solid, the overlay accretes writes (last-write-wins), reads_so_far fills (paths only). Toggle SKIP on an overlay/read action for a pure client-side re-fold what-if under a 'Hypothetical: action N skipped — [Revert]' banner; never a re-drive.
- INTENT≠EFFECT triage: a SOLID amber chip fires only when self-reported intent contradicts the observed op (says 'live' but is_cache=true, or names path A but read path B), never on absent intent, labeled 'possible mismatch — heuristic, not a verdict' — pointing at model-error vs data-error before you read anything else; also a ⚑ column on the Home run table so triage starts pre-open.
- Split lens over one cursor (power-user opt-in, ⌘\): split the lens stage to put PROFILE beside TIME-TRAVEL over the SAME cursor — scrub on the left, watch Most-Expensive-Ops re-rank on the right. Hidden by default (no dock tax for newcomers).
- Client-side column profiling on a real grid: select a column in the data.jsonl grid and the right panel computes null%/distinct/min-max/top-values or histogram from sampled rows; click a bar to filter the grid — labeled 'computed client-side, no live SQL' and shown MUTED next to SOLID table-level stats.json so engine-ish numbers are never confused with derived ones.
- Cmd-K as universal teleporter + the only home for governance: fuzzy across runs/paths/tables/ops/findings and verbs (switch lens, split lens right, open path in Data, Compare, Export .mirage-session), with Promote TEST→LIVE living here and nowhere else — governance demoted to a deliberate keystroke + a quiet branch chip.
- Pin to Investigation + Export/Import .mirage-session: ⌘⇧S snapshots the current {op, cursor permalink, note} into a durable saved-findings notebook whose chips reconstruct the exact debugger state; Export serializes actions[] + getSessionTrace + mount manifest so a teammate re-imports and scrubs offline deterministically (labeled 'scrub limited to overlay/reads/run; backing pinned at stand-up').

## Appendix F — Phased rollout

1. Phase 1 — Shell + Home + read-only Run debugger (the spine). Build the persistent three-band shell (context bar + two-tree rail + center) on the shipped consoleStore/sessionRunStore pattern; the cross-filter selection store {workspaceId,branch,runId,opIdx,path}; Home run-history grid (listSessions + rollups); and the Run debugger wired EXCLUSIVELY to getReplay + getSessionTrace with the TIME-TRAVEL lens (DIFF/STATE/ACTION over OverlayDiff), the By-Step INTENT+COMMAND cards, the causality-crumb inspector + anchor chip, and the transport. Re-fold stateAt(idx) client-side (port _fold_replay_state); fetch /replay once per run. Bake the solid/muted/dimmed tiers as shared primitives. Honest invariants stated in code: never the live useAgentStream reducer; reads_so_far 'paths only'. This phase alone answers 'model vs data?' for a single run.

2. Phase 2 — Snowflake-style Data View. Add the catalog tree's 13 mounts (lazy vfsList), the TABLE skin (stats.json strip SOLID, disabled query bar with NotImplementedError, Schema grid + static-labeled FK row, virtualized data.jsonl grid with per-column client-side profiling MUTED, ReservedMetadataStrip '—' on disk), and the FILE-TREE skin (vfsFile preview + honesty strip). Profile lens (operator tree + Most-Expensive-Ops rail + IO attribution; latency phases dimmed).

3. Phase 3 — The bridge + the rest of the webpage. Wire the bidirectional touched-by lineage (client get_vfs_ops join, 'this workspace's loaded runs not provenance' footer + 'load more runs', dimmed graph) as the Lineage lens AND the Data-View panel, made cross-linked via the shared selection. Add Compare (two runs), Investigation (investigationStore + /api/investigations, permalink finding cards), Cmd-K (teleporter + Promote-only governance), and Export/Import .mirage-session.

4. Phase 4 — Power-user polish + reserved-slot upgrades. Add the opt-in split-lens (⌘\) over one cursor; the matrix view on Home; the one-time 'lens keeps your op' coach-mark; and the clean-upgrade slots — flip the muted 'self-reported intent' chip to solid 'observed intent' (zero layout change) when a cognition plane lands, and light the dimmed latency-phase / lineage-graph / live-SQL slots if/when those endpoints emit. No redesign required; the honesty boundary visibly recedes as ground truth arrives.


## Appendix G — How this was produced

A 10-agent workflow over the real codebase: 3 reference deep-dives (Snowsight · Databricks · Redux+intent/command) → 3 full-webpage compositions → 3 judge personas → synthesis. Built on the converged `_v3_brief.md` and the verified Phase-0 endpoints. Artifacts: `_v3_brief.md`, `_v3_final.json`, `_v3_designs.json`, `_v3_verdicts.json`, `_v3_grounding.json`.
