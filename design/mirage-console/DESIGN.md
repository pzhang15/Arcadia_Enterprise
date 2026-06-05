# Mirage Console — Design Doc

> **Redux DevTools for your agent's data plane — scrub every action in a workspace, see the state it mutated, and trace any byte back to the step that touched it.**

**North star.** An engineer opens a mirage workspace and lives in one keyboard-driven organism all day: a chronological ACTION STREAM on the left, a reconstructed STATE TREE on the right, a TRANSPORT scrubber across the bottom, and an always-reachable DATA CATALOG that reverse-links any path to the actions that read or wrote it. The workspace is the store; real data-plane I/O are the actions; one time-travel cursor sweeps everything. It must feel like Redux DevTools / a source-level debugger — never a dashboard — and it must be honest to the byte: ground truth is rendered solid, inferred/derived is muted-and-labeled, and not-yet-emitted is a reserved dimmed slot we never fake.

---

## How to view the visual mockup

A self-contained, high-fidelity mockup of every screen lives in **`index.html`** (no build step — uses the real Arcadia design tokens: OKLCH dark theme, Inter + JetBrains Mono).

- **Open directly:** open `design/mirage-console/index.html` in any browser, OR
- **Serve it:** the Claude Code `mockup` launch config serves it at `http://localhost:4178`.

Each screen is captured as a numbered figure (Fig 00–07) below.

## Screen index

| Fig | Screen | What it answers |
|----|--------|-----------------|
| 00 | Overview / Redux mental model | How the whole thing is wired (Store=Workspace · Actions=I/O · State=reconstructed) |
| 01 | Workspace Home | The home: see EVERY trace and EVERY action in the workspace at once, scan runs for the failing one, and drop the cursor anywhere to start scrubbing. |
| 02 | Time-Travel | THE Redux DevTools centerpiece: scrub a chronological action stream with a cursor that reconstructs and diffs workspace state at any action. |
| 03 | By-run/step grouping lens | Collapse the same flat actions into the Session›Run›Step›ToolCall›VfsOp waterfall so a dev can debug one trace among ALL traces without leaving the spine. |
| 04 | Data focus | Browse the workspace's mounted backends as a live VFS catalog (first-class pillar, not a strip) and reverse-link any path to the traces that touched it — the bidirectional data↔trace bridge and the wrong-file/stale-read workflow. |
| 05 | Action lens | The DevTools 'Action' tab: inspect the exact wire payload of the selected event for low-level debugging, with honest provenance (which stream, which counter, which correlation ids are present/absent) and a copyable permalink. |
| 06 | Compare | Diff workspace state (or a single path) between two actions/runs — a lightweight branch-vs-branch or before-vs-after lens that pinpoints when behavior diverged. |
| 07 | Cmd-K command palette + Import/Export session bundle | Keyboard-first 'go to anything' across paths, runs, and action indices, plus the import/export of a portable, replayable session bundle — turning a debugging session into a shareable artifact (Redux import/export). |

---

# Mirage Console — Final Design Doc

## 0. The reframe, in one paragraph

Mirage Console is a **workspace-scoped developer debug console** with the feel of **Redux DevTools docked over a running app**. The workspace is the *store*; the real data-plane I/O that mirage observes at `observe.context.record()` (path · bytes · source · cache · fingerprint) are the *actions*; a single **time-travel cursor** sweeps a chronological action stream and reconstructs workspace state at any point. It sees **all traces and all events** in the workspace, and — because mirage *is* the data plane — it is simultaneously a **live explorer of the connected sources** with a **bidirectional data↔trace bridge** ("who touched this byte?"). Governance is demoted to quiet per-write decorations. Everything is rendered solid where the plane emits ground truth, muted-and-labeled where it is inferred/derived, and reserved-dimmed where it is not yet emitted.

## 1. The synthesis decision (why this shape)

We had three competing paradigms and three judge verdicts. The verdicts converge with unusual clarity, so the synthesis is not a compromise — it is an assembly with one clear spine and two named grafts.

- **Spine — Mirage Console** is the SKELETON. It is the only design that takes "Redux DevTools, literally" at its word: a single persistent two-pane organism (Action List + State Inspector) with a transport pinned across the bottom, and **lenses instead of pages** (Diff / State / Action / Trace / Data are tabs over the *same* selected action and the *same* cursor). Two judges made it their topPick (58/58); the third (the UX judge who picked Sourcescope) still said "Spine has the strongest FEEL" and explicitly advised building on Spine's shell. It earns the feel through the one move no wrapper competitor can make truthfully: the **exact per-action Diff** for a VfsOp, because the gap-free trajectory `idx` equals the position in `ws.ops.records`, so *action N IS `OpRecord[N]`*.
- **Sourcescope** is the SOUL. Its "find-usages for data" inversion ("who read/wrote this byte?") is, per all three judges, the single best idea in the set, and the join is provably EXACT off `_console_trajectory`'s `mount_prefix + path`. On *this* demo — northhill_corp mounts **12 read-only sources** and only `/` (RAM) + `/tickets` are writeable — the wrong-file / stale-read data-correctness workflow is the richest story the console can tell. So we **reject Spine's demotion of data to a 36px strip** and promote Sourcescope's catalog to a first-class, always-reachable pillar.
- **Workbench** contributes exactly TWO things every judge named and Spine genuinely lacks: (a) a **dedicated, always-cheap All-Traces run-rail overview** (the fastest "which of my N runs is red" glance), and (b) the **one-cursor-drives-every-panel synchronization contract**. We decline its five-draggable-panel dock manager — lowest implementability (5) and learnability (5) across all three designs, with named perf/jank risk for no proportional debug payoff.

The resolution of the Spine-vs-Sourcescope tension (trace-first vs data-first IA) is the UX judge's exact prescription: **do not route modes and do not pick a front door.** Ship two *layout presets* — **Time-Travel focus** (action list + state inspector dominant) and **Data focus** (catalog + Touched-by dominant) — as two arrangements of the SAME panels and the SAME cursor. Default to Time-Travel focus (familiar, trace-centric); make Data focus one keystroke away and bidirectionally linked.

## 2. First-principles reasoning (what mirage uniquely affords, and what it does not)

A debugger is only as good as its ground truth. Every wrapper-based competitor (LangSmith/Langfuse/Phoenix/Helicone/OTel) records what the agent *self-reported* — if the model paraphrases, truncates, or lies about which file it read, their trace is silently wrong. Mirage sits *between* the reasoning and the data plane and observes the real op. Five consequences drive every design decision:

1. **The action stream is real I/O, not tool args.** A VfsOp row is the observed `OpRecord` (op·path·source·bytes·duration_ms·mount_prefix), surfaced via `_console_trajectory`. This is the substrate the whole organism stands on.
2. **State reconstruction is deterministic and exact on the right layers.** `replayAguiEvents` is a verified pure fold-from-empty (`aguiEventReducer.ts` L341). The trajectory `idx` is gap-free (`enumerate(ws.ops.records)`), so folding `[0..idx]` of overlay / reads-so-far / pending-effects / run-sub-tree is exact and re-derivable. **Backing FS of written mounts is pinned once at stand-up** (`pinned_backing` on `ConsoleWorkspaceDetail`) and is NOT re-derivable per-tick — we label it, never fake byte-exact full-FS rewind.
3. **The data↔trace bridge is a real client-side join.** `_console_trajectory` carries `mount_prefix + path`, so "every op that touched this path" is an exact filter. This is the moat made literal: IDE *find-usages*, where the symbol index is the mount catalog and the call sites are traces/steps.
4. **Two counters, one timeline — and we are honest about the seam.** The relay firehose (`useEventStream('/events')`) carries a stable global `seq`; AG-UI events (`getSessionTrace`) bypass `_persist_and_broadcast` and carry only a per-session seq. No single monotonic key spans both, so the merged order is by **timestamp**, with same-ms ties rendered as an "inferred order" hairline and the row gutter showing `seq` vs `§seq` so the dev never thinks they are one counter. For state reconstruction we **prefer the gap-free trajectory idx**, the cleanest cursor.
5. **Attribution op→step is inferred until Phase-0.** `correlateEventsToSteps` (verified) assigns the *last* timestamp-matching step, so overlapping/zero-duration steps mis-bucket. Every grouped/bridged row wears an "inferred" dot until `tool_call_id` is stamped at emission.

What mirage does NOT afford today, rendered as reserved dimmed slots, never fabricated: lineage/provenance graph (OpenLineage `emit_*` is NotImplementedError), policy/ACL/budget decisions (PolicyEngine never called at the VFS boundary), credential/token lifecycle (broker stubs), PII findings (none), live SQL/glob/similarity (`query.json` + catalog-proxy are 100% NotImplementedError), and `STATE_SNAPSHOT`/`STATE_DELTA` (enum-only — `types/agui.ts` L17-18 — never emitted/reduced/stored).

## 3. The object model & the spine

**TOP-LEVEL CONTAINER = workspace.** A slim 44px global header holds only: a workspace switcher combobox (`consoleStore.workspaces`, persisted to localStorage), the active branch chip + a 1-char mono mode glyph (`T`/`L`, never red chrome), a connection dot + **persisted/in-memory pill** (prominent, because a console watching ALL events goes empty after restart if not arcadia_store-backed), a layout-preset toggle (Time-Travel ⇄ Data), and a Cmd-K command palette.

The data spine (the trace tree) is preserved verbatim and is the grouping skeleton of the action list:

```
Session (≈ workspace/branch; thread_id)
 └─ Run (run-{uuid}; one user turn; trace root)  ── joins ScoreCard · relay events by run_id
     └─ Step (step-N; one agent-loop iteration; reasoning + tool_call_ids[])
         ├─ Reasoning (THINKING_* / TEXT_*)
         └─ ToolCall (tc-{uuid}; tool_name='exec'; args=raw shell; result=stdout+exit)  == one Workspace.execute()
             └─ VfsOp (OpRecord: op·path·source·bytes·duration_ms·mount_prefix·fingerprint·revision·is_cache)  ← GROUND-TRUTH LEAF
                 └─ decorations: EffectClass · CaptureState · Cache/Latency phase · [Lineage · Policy — reserved dimmed]
```

The shell is a fixed, resizable, collapsible three-region grid that never unmounts (NOT routed pages — this deletes today's `ConsoleLayout` SUB_NAV router):

- **LEFT RAIL (380px default, resizable):** the unified ACTION LIST — one virtualized stream of every action in the workspace, with a type-chip filter bar pinned at top, a Flat ⇄ By-run/step **grouping toggle**, and the transport footer at the bottom.
- **CENTER+RIGHT (fluid):** the STATE INSPECTOR for the action under the cursor, with a lens tab strip at the very top (**Diff · State Tree · Action · Trace · Data**) — tabs over the same selected action, not routes.
- **TRANSPORT BAR (bottom, 36px, full width):** the time-travel scrubber — a density mini-map of the action stream with a draggable playhead, play/pause/step-back/step-fwd/jump-to-end, a 1×/2×/4× speed control, and `cursor #K of M · seq 4188 · 12:04:07.214`.
- **DATA PILLAR (right, promotable):** the Data Sources catalog. In Time-Travel focus it is a collapsible right surface; in Data focus it is dominant. It is a **first-class pillar, not a 36px strip** — this is the deliberate departure from Spine.

The two shared, URL-addressable selections are the **cursor (idx)** and the **path** — so any cross-pillar view is a permalink: `/w/:workspaceId?cursor=:idx&lens=diff&group=step&path=/s3/...&preset=data`.

## 4. The Redux mental model (mapped to real plumbing)

- **ACTION LIST ← the merged event stream.** Relay firehose (`useEventStream`, global `seq`: command/op/agent_status/agent_thinking/mock_request/mcp_tool_call/console_*) UNION per-session AG-UI events (`getSessionTrace` → RUN/STEP/THINKING/TEXT/TOOL_CALL/CUSTOM(vfs_op)). Merge key = timestamp; gutter shows `seq` (firehose) vs `§seq` (agui); same-ms collisions get an "inferred order" hairline. **VfsOp rows prefer the trajectory/agui source** — because relay `op` events are capped at the last 20 per command (`server.py` L1006 `new_records[-20:]`) while the AG-UI CUSTOM path is uncapped; any firehose-only discrepancy is flagged.
- **STATE TREE ← reconstructed state at the cursor**, folded from `trajectory[0..idx]` plus the AG-UI reducer sliced to the cursor timestamp. Four solid nodes, each backed by a real endpoint: **overlay** (`getOverlay` mounts[].changes, change key `idx:op:path` — the `OverlayDiff` seed), **mounts** (`getConsoleWorkspace.mounts`: prefix/resource/mode/effect_class), **reads-so-far** (read ops ≤ idx from `getTrajectory`), **run** (runs/steps/toolCalls/messages from `replayAguiEvents`). A fifth node, **state (snapshot)**, is rendered as a reserved dimmed "not yet emitted" stub (STATE_SNAPSHOT/STATE_DELTA are dead enum names).
- **PER-ACTION DIFF ← `diff(stateAt(idx-1), stateAt(idx))`.** For a VfsOp the diff is EXACT and trivial — action idx == `OpRecord[idx]` — rendered as a git-style hunk via the existing `OverlayDiff` renderer (op icon, path, ±bytes, capture badge, effect-class dot). For run-level actions, diff successive reducer snapshots (a new message delta, a step boundary, a tool result arriving).
- **JUMP-TO ←** click an action → `cursor = idx`, re-fold `[0..idx]` (pure client-side, deterministic). **SKIP-ACTION ←** right-click → Skip re-folds `[0..idx]` minus the skipped idx under a "hypothetical: action N skipped" banner with one-click revert; **enabled** for overlay/reads/run layers (recomputable), **disabled with a tooltip** for backing-dependent state. It is a state-reconstruction what-if, not a real re-drive.
- **FUTURE-DIMMING ←** every row and mini-map segment past the cursor at ~45% opacity with a "not yet executed" left border. Live tail auto-advances the cursor unless pinned (Redux pause).
- **IMPORT/EXPORT ←** Export generalizes the verified `TrajectoryPage.exportJson` to a `.mirage-session.json` (merged action log + agui trace + overlay snapshot + mount manifest). Import re-hydrates via `replayAguiEvents` into a read-only "replaying saved session" with the cursor enabled and live tail disabled; backing reconstruction is honestly marked deferred (pinned at stand-up).

## 5. The data-source exploration + bidirectional bridge

The Data Pillar treats mirage's unified VFS for what it is: a **mount tree + per-path file browser**, because on the shipped demo every "exotic" backend is a `Fake*Resource(DiskResource)` — JSON/JSONL on disk dressed as S3/Slack/Postgres/Datadog. We do NOT build per-backend native widgets; we build ONE honest tree + preview, plus a type-aware skin.

- **TOP LEVEL = mount catalog** from `_console_mounts_detail`: each row shows prefix (`/`, `/slack`, `/sheets`, `/gdocs`, `/tickets`, `/github`, `/pagerduty`, `/datadog`, `/finance`, `/customers`, `/compliance`, `/database`, `/s3`), resource type, mode (ro/rw chip), a quiet **effect-class dot** (scratch / durable-internal / system-of-record / external-effect) with a reversibility tooltip, a 1-line **"browsed as: file tree / table (cat·ls)"** subtitle, and a right-aligned derived **"touched by N traces"** rollup.
- **FILE-TREE skin** (most mounts): lazy `vfsList` (`ls -la` → `_parse_ls_output` → {name,type,size} only) + `vfsFile` (`cat`) preview, JSON pretty-printed, with a mandatory honesty strip: **"preview only · text decode · no binary/truncation detection"** and a truncated marker on large files.
- **TABLE skin** (`/database`, grafted from Sourcescope): when a directory matches `tables/<t>/{schema.json,data.jsonl,stats.json}`, render a **TableCard** — Schema sub-tab (columns/types/PK/FK grid), Rows sub-tab (virtualized grid of `data.jsonl`), Stats strip (row_count/size/last_updated). A persistent **"derived from files on disk — no live SQL"** note; the query bar is present but DISABLED with tooltip **"live query.json / catalog-proxy — schema designed, NotImplementedError."**
- **Reserved metadata strip** on every file (fingerprint / revision / modified / mode / consistency): shown as `—` with **"not surfaced (ls -la drops these; only S3 SUPPORTS_SNAPSHOT populates ETag/revision)"** — never fabricated drift UI on disk doubles.

**THE BIDIRECTIONAL BRIDGE (the moat, both directions, always-on):**

- **Data → trace (find-usages for data):** click a path's "N traces" gutter → the right inspector's **Touched-by** list shows every op whose `mount_prefix + path` matches (exact, from `getTrajectory`), grouped by run | op, each with op·source·bytes·duration_ms·effect_class and the *inferred* owning step. A **read/write sparkline** ("written once, read 30×") makes the wrong-file/stale-read pattern visible at a glance. Click a usage → the **global cursor jumps** to that op; the Diff lens highlights exactly that op.
- **Trace → data (automatic inverse):** when the cursor lands on a VfsOp action, the Data Pillar **auto-reveals and rings** that path (scroll-into-view + highlight). "Who touched this byte" and "what did this action touch" are one gesture from two directions.

**Named first-class workflow — wrong-file / stale-revision (grafted from Sourcescope):** start at a suspect path → Touched-by shows a *sibling/older* path was read instead → jump to that op → scrub state to confirm what had (not) been read yet → optionally Compare the two runs to pinpoint the divergence. On 12 read-only sources this is the highest-value real-world agent bug and the thing only a mirage-native console can debug.

## 6. Information architecture

- **Container:** workspace (switcher in the 44px header). Everything below is "everything that happened in this workspace."
- **No page-switcher.** Navigation is *cursor movement + lens selection + layout preset*, not routing.
- **All traces ⇄ single trace:** the left-rail **grouping toggle** Flat ⇄ By-run/step morphs the same action set in place (Spine's lens move), PLUS a dedicated **All-Traces run-rail** overview (Workbench's graft) for the instant "which run is red" glance. Selecting any node or lane moves the one cursor / scopes the spine.
- **Single trace ⇄ event log / time-travel:** the same thing — the cursor always exists; the transport animates it.
- **→ data sources:** flip to Data focus (one keystroke) or expand the pillar; browse data while the timeline stays visible.
- **Data → traces:** Touched-by reverse-link; the inverse is automatic.
- **Lenses over one action:** Diff / State Tree / Action / Trace / Data.
- **Permalink scheme:** `/w/:workspaceId?cursor=:idx&lens=:lens&group=:flat|step&path=:path&preset=:tt|data` — cursor and path are the two shared addressable selections.

## 7. Feasibility & rollout honesty

Buildable now on existing endpoints/components: the full Session›Run›Step›ToolCall waterfall (reducer/store/replay exist; `RunTracePanel`/`StepCard`/`ToolCallRow`/`ReasoningBlock`), the run/session list (`listSessions`/`getSessionTrace`), the relay firehose (`useEventStream` + `stream_events`), the op log + filters + export (`TrajectoryPage`), the overlay hunk renderer (`OverlayDiff`), the VFS browser (`vfsList`/`vfsFile`), the mount catalog + effect-class (`_console_mounts_detail` + `effectClass`/`mountColor`/`EffectClassTag`/`CaptureBadge`), workspace switching/branching (`consoleStore` + `BranchTree`).

The one net-new core engine all panels share: a **deterministic client-side fold of `trajectory[0..idx]`** (`stateAt(N)`) over `_console_overlay` (change key `idx:op:path`) + `_console_trajectory` + `_console_effects`, plus `replayAguiEvents` sliced to the cursor timestamp. The time-travel cursor does NOT exist today (verified: only CSS `cursor:` refs). Build it once, share it everywhere.

Two non-negotiable backend dependencies, sequenced explicitly: **(a) arcadia_store-backed pagination/virtualization from day one** — a console watching ALL workspace events cannot ride the 2000-event RAM ring (`MAX_EVENTS=2000` in `useEventStream`) or it truncates/goes empty after restart; surface the persisted-vs-in-memory pill prominently, and note `runs/steps/tool_calls/vfs_ops` are currently WRITE-ONLY (historical post-restart views need new read queries). **(b) Phase-0 emission fix** — stamp `tool_call_id`/`step_id`/`run_id` + restore the dropped `source`/`duration_ms`/`fingerprint`/`revision` onto every VfsOp at emission (`server.py` ~L1403), consume `ExecutionNode.records` instead of length-diffing `ws.ops.records`, fill `vfs_ops.tool_call_id` in the coalescer. This single fix simultaneously upgrades the merged-stream ordering from timestamp-approximate to exact AND upgrades every op→step attribution from inferred to joined — the highest-leverage backend work for the whole synthesis.

## 8. Honesty guardrails (the trust layer — non-negotiable, every caveat maps to real code)

- **Solid (ground truth, full color):** VfsOp rows and the per-action Diff (action idx == `OpRecord[idx]`); overlay/reads/mounts/run-sub-tree folds; the data→op join (`mount_prefix + path`); relay firehose with stable `seq`.
- **Muted-and-labeled (inferred/derived):** the timestamp merge (`seq` vs `§seq` gutter + "inferred order" hairline); op→step attribution ("inferred" dot until tool_call_id is stamped); "served from cache (derived)" chips (cache emits no OpRecord — never a phantom action); derived latency phases (model vs cache vs byte-fetch); the firehose 20-op cap discrepancy flag.
- **Reserved dimmed (not yet emitted, never faked):** "state (snapshot)" node (STATE_SNAPSHOT/STATE_DELTA dead enum); lineage / policy / credential / PII rails; the disabled query bar (catalog-proxy NotImplementedError); greyed fingerprint/revision/consistency on disk-backed sources; the "preview only / truncated / binary" strip on cat output; "backing pinned at stand-up" on written-mount full-FS time travel.
- **Governance demoted everywhere:** effect-class dot + reversibility tooltip as quiet per-write decorations; a non-alarming 1-char mode glyph; promote reachable only from Cmd-K — never a modal front door, no LIVE red chrome, no pending-effects counter in the chrome.

---

## Appendix A — Build-ready screen specifications

### Fig 01 · Workspace Home — All-Traces run-rail + flat action stream

**Purpose.** The home: see EVERY trace and EVERY action in the workspace at once, scan runs for the failing one, and drop the cursor anywhere to start scrubbing. Grafts Workbench's dedicated run-rail onto Spine's flat stream so 'which of my N runs is red' is an instant glance, not a derived re-render.

**When used.** First thing on opening a workspace; whenever the dev wants the bird's-eye 'what has happened here' view before drilling into one trace.

**Layout.** Global header 44px (workspace switcher · branch chip + mode glyph T · conn dot + 'persisted' pill · layout toggle [Time-Travel selected] · Cmd-K). Below, three regions. LEFT RAIL 380px: a thin ALL-TRACES run-rail strip pinned at the very top (~140px, newest-first, virtualized run lanes), then the type-chip filter bar, then the virtualized flat ACTION LIST (reverse-chron), then the per-rail status line. CENTER+RIGHT fluid: lens tab strip (Diff·State Tree·Action·Trace·Data) with State Tree active by default, showing the 4 collapsible nodes folded to the cursor. TRANSPORT BAR 36px full-width bottom. DATA PILLAR collapsed to a slim right surface (mount-dot column).

**Key components.** RunLaneRail (run-{uuid} · started_at · status dot · steps/tools/ops/bytes rollup · mini latency bar; newest-first; click scopes the spine); TypeChipFilterBar (RUN/STEP/THINKING/TEXT/TOOL_CALL/vfs_op/command/mock + path search + capture facet); VirtualActionList (ActionRow: gutter seq/§seq · type chip · payload summary · Δ badge · effect-class dot for writes; future-dimming past cursor); StateTreeInspector (overlay / mounts / reads-so-far / run + reserved dimmed 'state (snapshot)' node); TransportBar (mini-map + playhead · play/step/jump · speed · CursorBadge); PersistedPill ('persisted' vs 'in-memory — trace empty after restart')

**Sample data (as rendered in the mockup).** Workspace switcher: 'northhill-incident-fc92 · branch main · T'. Run rail (newest-first): run-9f2c1a 'forensic RCA INC-5521' 14:03:07 status RED(error) · 4 steps · 11 tools · 38 ops · 1.4 MB · 312ms bar; run-7be004 'customer revenue Q1' 11:48:22 GREEN · 3 steps · 6 tools · 19 ops · 842 KB; run-22af90 'enterprise review GlobalTech' 09:12:55 GREEN · 5 steps · 14 tools · 51 ops · 2.1 MB. Action list (flat, reverse-chron), gutter | type | summary | Δ: §312 TOOL_CALL_RESULT 'exec exit_code=0' ; §311 CUSTOM(vfs_op) 'write /rca_inc_5521.md +4.2 KB' Δ+1 (durable dot) ; §310 CUSTOM(vfs_op) 'read /slack/channels/incidents__C305/bridge.jsonl 18 KB' ; seq 4188 op 'read /github/repos/northhill/platform-api/commits/f3a1b2c8.json 2.0 KB' ; seq 4187 command 'cat /github/.../commits/f3a1b2c8.json exit 0' ; §305 THINKING_CONTENT 'correlating deploy time to first error…'. Status line: '419 actions · 3 runs · showing 419'. CursorBadge: '#312 of 419 · §312 · 14:03:41.187'.

**Signature interaction.** Dev opens the workspace, sees run-9f2c1a glowing red in the rail, clicks it → the spine scopes to that run, the action list jumps to the run window, the cursor auto-parks on the last action before RUN_ERROR, and the State Tree shows the overlay/reads at the failure point. Then Home jumps to action #1 and Space plays: the mini-map playhead sweeps right, ActionRows light in sequence, and the overlay node grows /rca_inc_5521.md exactly when the write fires.

### Fig 02 · Time-Travel — Event Log + State Tree + per-action Diff (Redux centerpiece)

**Purpose.** THE Redux DevTools centerpiece: scrub a chronological action stream with a cursor that reconstructs and diffs workspace state at any action. The exact VfsOp Diff (action idx == OpRecord[idx]) is the killer lens no wrapper competitor can make truthfully.

**When used.** The 90% screen — op-level debugging, 'what did THIS action change', 'what had been read by the time of the write', skip-action what-if, export-the-repro.

**Layout.** Same shell, Time-Travel focus, lens = Diff (toggle to State Tree). LEFT RAIL 380px: filter bar + virtualized action list with future-dimming. CENTER+RIGHT: lens strip; Diff body = top ActionSummaryCard over a DIFF BODY (git-hunk for writes; read-preview card for reads; structural diff for run-level actions) + a right SiblingCollisionList ('also at this timestamp'). Toggling to State Tree shows the 4 nodes folded to the cursor with the mutated subtree ring-highlighted. TRANSPORT BAR bottom with the draggable playhead; the segment past the cursor dimmed. A 'hypothetical: action N skipped' banner appears across the inspector when a skip is active.

**Key components.** VirtualActionList (future-dimming + seq/§seq gutter + 'inferred order' hairline on same-ms ties); ActionSummaryCard (type · idx · timestamp · source · duration_ms · effect-class dot + reversibility tooltip · 'served from cache (derived)' chip when applicable); OverlayHunk (reuses OverlayDiff: op icon · path · ±bytes · capture badge); ReadPreviewCard (getConsoleFile, 4000-char cap, 'preview only · text decode · no binary/truncation detection' strip); StructuralRunDiff (+ message delta / + step started / + tool result exit_code); SkipWhatIfBanner ('hypothetical: action N skipped — revert'; enabled for overlay/reads/run, disabled w/ tooltip for backing); ScrubberPlayhead (density sparkline over wall-time + future-dimming); Export/Import session bundle buttons

**Sample data (as rendered in the mockup).** Cursor on op idx 57, a write to /rca_inc_5521.md. ActionSummaryCard: 'CUSTOM(vfs_op) · idx 57 · 14:03:41.187 · source=ram · 6ms · durable-internal ●' (tooltip: 'Durable internal — reversible via overlay reset, not yet promoted'). DIFF BODY: single green hunk '+ /rca_inc_5521.md  +4.2 KB' (write icon, captured badge). SiblingCollisionList: '2 actions share 14:03:41.187 — order inferred (§57 vfs_op · §57b TEXT_MESSAGE_CONTENT)'. State Tree at idx 57: overlay { '/': [ '/rca_inc_5521.md +4.2 KB' ] }, reads-so-far { 47 paths: /pagerduty/incidents/triggered/INC-5521.json, /datadog/logs/platform-api/2026/05/15/*.jsonl, /github/.../commits/f3a1b2c8.json, … }, mounts {13}, run { run-9f2c1a › step-4 › tc-aa31 }, state (snapshot) [dimmed: 'not yet emitted']. A 'served from cache (derived)' chip sits on the prior /database read (source==ram, no network op).

**Signature interaction.** Dev drags the playhead back to action #88 (a read of /database/tables/users/data.jsonl); everything after #88 dims; the State Tree shows the overlay before /rca_inc_5521.md existed and reads-so-far proves only 12 paths had been read. Dev right-clicks a redundant re-read at #92 → Skip → 'hypothetical: action 92 skipped' banner; State re-folds without it, proving the later write didn't depend on it. Dev clicks Export session bundle to hand the repro to a teammate.

### Fig 03 · By-run/step grouping lens — the Trace waterfall, in place

**Purpose.** Collapse the same flat actions into the Session›Run›Step›ToolCall›VfsOp waterfall so a dev can debug one trace among ALL traces without leaving the spine. The trace viewer is a LENS, not a page.

**When used.** End-to-end debugging of one run: reasoning → tool calls → the VfsOp ground-truth leaf, with latency phases and drift flag; picking which op caused which mutation.

**Layout.** Same shell; LEFT RAIL grouping toggle flipped to 'By run/step', re-rendering the identical action set as an indented collapsible tree (Run › Step › ToolCall › VfsOp). CENTER+RIGHT lens = Trace: a RunRollup header, then the selected node's latency-phase bars (model vs cache-derived vs byte-fetch) over a CorrelatedVfsOpTable (op·path·source·bytes·duration·effect-class). Cross-highlight: hovering a step rings its child ops in the tree and the touched paths in the Data Pillar strip. TRANSPORT BAR bottom unchanged — selecting any leaf still drives the one cursor.

**Key components.** RunStepTree (indented, collapsible; 'inferred' dot on grouped ops until tool_call_id is stamped); RunRollup (n_ops · bytes · cache_hit_rate derived · optional ScoreCard join by run_id when offline results exist); TraceLensPanel (latency-phase bars; derived cache phase labeled); CorrelatedVfsOpTable (reuses TrajectoryPage row vocabulary); DriftFlag (only live when S3 ETag/revision present; greyed on disk-backed mounts); CrossHighlightController (step ↔ ops ↔ data-path ring sync); PerNodePermalink (copy-link restoring run+step+leaf)

**Sample data (as rendered in the mockup).** Tree: Run-9f2c1a (RED · 4 steps · 38 ops · 1.4 MB) › Step-3 'establish causal deployment' (3 tools) › ToolCall tc-aa31 'exec: cat /github/repos/northhill/platform-api/commits/f3a1b2c8.json' (exit 0) › VfsOp idx 41 'read /github/.../commits/f3a1b2c8.json · github · 2.0 KB · 4ms · durable ●' [inferred dot]. RunRollup: '38 ops · 1.4 MB · cache_hit_rate 0.21 (derived) · within_budget ✓ (ScoreCard run-9f2c1a)'. Trace lens for tc-aa31: phase bar '220ms model · ~0ms cache (derived) · 4ms fetch'; CorrelatedVfsOpTable: idx41 read /github/.../f3a1b2c8.json 2.0KB; idx42 read /github/.../deployments/2026-05-15.json 1.1KB. DriftFlag greyed: 'not surfaced — github is disk-backed; no ETag'.

**Signature interaction.** Dev flips grouping to By-run/step, expands Run-9f2c1a › Step-3, clicks ToolCall tc-aa31; the Trace lens shows its phase bar and the 2 VfsOps it caused; an 'inferred' dot on the ops opens a tooltip 'attributed by event ordering; tool_call_id not yet stamped'. Hovering Step-3 rings its child ops AND the /github paths in the Data Pillar strip. Clicking idx 41 moves the global cursor there; switching to the Diff lens shows the exact read.

### Fig 04 · Data focus — Connected sources catalog + TableCard + Touched-by bridge

**Purpose.** Browse the workspace's mounted backends as a live VFS catalog (first-class pillar, not a strip) and reverse-link any path to the traces that touched it — the bidirectional data↔trace bridge and the wrong-file/stale-read workflow. Grafts Sourcescope's catalog/TableCard/find-usages onto the shared cursor.

**When used.** Data-correctness debugging: 'did the agent read the wrong/stale file?', exploring an unfamiliar source, confirming a written file's bytes, finding every step that touched a path.

**Layout.** Same shell, Data focus preset: DATA PILLAR becomes dominant (center+left), the action list compresses to a 280px right sidebar (still cursor-linked). LEFT (300px): mount catalog list (prefix · resource · ro/rw chip · effect dot · 'touched by N traces' rollup · 'browsed as:' subtitle). CENTER: type-aware browser — FILE-TREE skin (lazy vfsList tree + breadcrumb + vfsFile preview with honesty strip) OR TableCard skin for /database (Schema / Rows / Stats sub-tabs + disabled query bar). RIGHT INSPECTOR (400px) 'Touched-by': find-usages list for the selected path (grouped by run|op) + read/write sparkline + deep-links. When a path is selected the right action-sidebar flips to 'touched by' filter mode.

**Key components.** MountCatalog (effect dot + reversibility tooltip; 'browsed as: file tree / table' subtitle; derived touched-by rollup); LazyVfsTree (vfsList, {name,type,size} only) + FilePreview (vfsFile, JSON pretty, 'preview only · text decode · no binary/truncation detection' strip + truncated marker); TableCard (Schema grid from schema.json · Rows virtualized grid from data.jsonl · Stats strip from stats.json; 'derived from files — no live SQL' note); DisabledQueryBar (tooltip 'live query.json / catalog-proxy — schema designed, NotImplementedError'); ReservedMetadataStrip (fingerprint/revision/modified/consistency = '—', 'not surfaced — ls -la drops these; S3-only via ETag'); TouchedByPanel (getTrajectory filtered by mount_prefix+path; grouped by run|op; 'INFERRED attribution' chip; read/write sparkline); ReverseLinkController (path → filter action sidebar to touched-by; cursor jump on click; auto-ring on inverse)

**Sample data (as rendered in the mockup).** Mount catalog (13): / RAM rw scratch ● · /slack disk ro external-effect ● 'browsed as: file tree' · 9 traces; /database disk ro system-of-record ● 'browsed as: table' · 4 traces; /s3 disk ro durable-internal ● · 11 traces; /tickets disk rw durable-internal ● · 6 traces; /github · /pagerduty · /datadog · /customers · /finance · /compliance · /sheets · /gdocs (all ro). TableCard for /database/tables/users: Schema grid — user_id varchar(36) PK · account_id varchar(16) · email varchar(255) · created_at timestamptz · last_login timestamptz null · plan varchar(32) · status varchar(32). Stats strip: 'row_count 500 · size 105,590 B · last_updated 2026-05-15T12:00:00Z'. Rows head: {user_id usr_00000, account_id ACCT-2024, email arodriguez@example.org, plan free, status active}. Touched-by for /database/tables/users/data.jsonl: header '5 actions touched this — 4 read / 1 write'; rows — read idx88 1 KB ram 3ms run-7be004/step-2 [inferred]; read idx92 1 KB ram 2ms run-7be004/step-2 [inferred]; sparkline 'written 0× · read 5×'. Reserved metadata strip on a /s3 file: fingerprint — , revision — ('not surfaced — disk-backed; S3-only via ETag').

**Signature interaction.** Wrong-file investigation: dev opens /database → tables → users → Rows, eyeballs the data, clicks 'Touched-by' and sees a SIBLING table users_2023 was also read by run-7be004/step-2 — they suspect the agent read the stale table. They click that read op → the global cursor jumps there, the Diff lens highlights the exact read, and the action sidebar confirms what had/hadn't been read yet. The inverse is automatic: parking the cursor on any /github VfsOp auto-reveals and rings that file in the catalog tree.

### Fig 05 · Action lens — raw event payload + provenance + permalink

**Purpose.** The DevTools 'Action' tab: inspect the exact wire payload of the selected event for low-level debugging, with honest provenance (which stream, which counter, which correlation ids are present/absent) and a copyable permalink.

**When used.** When a dev needs the raw event dict for a bug report, to see exactly which fields the emission path dropped, or to grab a permalink to a precise action+lens.

**Layout.** Same shell; lens = Action. Inspector body = a syntax-highlighted, collapsible JSON view of the raw event dict, a StreamProvenanceHeader (type · source stream relay/agui · seq or §seq · thread_id/run_id/step_id/tool_call_id when present), a DroppedFieldsNote (honest list of fields the wire form omits), and a Copy-permalink button. LEFT RAIL + TRANSPORT unchanged.

**Key components.** RawEventJson (collapsible, copyable); StreamProvenanceHeader (relay vs agui · which counter · correlation ids present/absent); DroppedFieldsNote (honest list of fields the emission path discards); PermalinkButton (/w/:id?cursor=:idx&lens=action)

**Sample data (as rendered in the mockup).** Selected: a CUSTOM(vfs_op) at §57. RawEventJson: { type:'CUSTOM', name:'vfs_op', value:{ op:'write', path:'/rca_inc_5521.md', bytes:4280, mount_prefix:'/' }, timestamp:1747315421187 }. ProvenanceHeader: 'source=agui · §seq 57 · thread_id=northhill-incident-fc92 · run_id=run-9f2c1a · step_id=(absent) · tool_call_id=(absent)'. DroppedFieldsNote: 'This event dropped source / duration_ms / fingerprint / revision / is_cache and carries no step_id or tool_call_id — op→step link is inferred (Phase-0 fix: server.py ~L1403).' Permalink: /w/northhill-incident-fc92?cursor=57&lens=action.

**Signature interaction.** Dev clicks a vfs_op action, switches to the Action lens, reads the dropped-fields note explaining why attribution is inferred, and copies the permalink to paste into a bug ticket. A teammate opens the link and lands on the exact action with the Action lens active.

### Fig 06 · Compare — two cursors / two runs side-by-side (lighter lens)

**Purpose.** Diff workspace state (or a single path) between two actions/runs — a lightweight branch-vs-branch or before-vs-after lens that pinpoints when behavior diverged. Kept light per the reframe (not a pillar).

**When used.** Confirming a regression: 'run-7 read the wrong file where run-5 read the right one'; comparing overlay state across a branch fork; before/after a fix.

**Layout.** Inspector switches to two-column mode launched from Cmd-K or a Touched-by 'compare runs' action. LEFT = state at cursor A (a pinned trajectory idx), RIGHT = state at cursor B (possibly a different run/branch via consoleStore.workspaces). Center gutter shows added/removed/changed overlay paths and marks the FIRST divergent op (different path/bytes/source for the 'same' logical step). A path picker offers a single-file side-by-side (vfsFile A vs B) with a simple line diff and a 'text-only preview' label. A DualCursorBar (pin A / pin B) sits above.

**Key components.** DualCursorBar (pin A / pin B; branch source selector reuses BranchTree); StateColumn x2 (folded overlays at A and B); OverlayPathDiff gutter (added/removed/changed); FirstDivergenceMarker (path/bytes/source mismatch); FileSideBySide (vfsFile A/B line diff, 'text-only preview'); SummaryDeltaHeader (ops A vs B · bytes A vs B · first-divergence time)

**Sample data (as rendered in the mockup).** A = end of run-7be004 (branch main); B = end of run-7be004-fork (forked branch). SummaryDeltaHeader: 'A 19 ops / 842 KB · B 21 ops / 905 KB · first divergence 11:49:02'. Gutter: first-divergence marker 'step-2 read: A=/database/tables/users/data.jsonl vs B=/database/tables/users_2023/data.jsonl'. Overlay diff: /scratch/summary.md changed; /database untouched in both. FileSideBySide on summary.md: A 1.1 KB vs B 1.6 KB, +14 lines (B longer).

**Signature interaction.** From Touched-by on users/data.jsonl the dev clicks 'compare runs 5 & 7'; the gutter flags that run-7 read users_2023 where run-5 read users — the exact moment the wrong-file regression entered. Dev opens the file side-by-side to confirm, then closes Compare back to the single-cursor spine.

### Fig 07 · Cmd-K command palette + Import/Export session bundle

**Purpose.** Keyboard-first 'go to anything' across paths, runs, and action indices, plus the import/export of a portable, replayable session bundle — turning a debugging session into a shareable artifact (Redux import/export).

**When used.** All-day keyboard operation (jump to action by index, filter ops on a path, toggle lens/preset, copy permalink); handing a teammate 'here is exactly what my agent did' to scrub offline; demoted promote reachable here (never a modal front door).

**Layout.** Centered command palette overlay over the dimmed spine. Single fuzzy input; grouped results: 'Sources' (paths from trajectory distinct paths + mount prefixes), 'Runs' (run-id / start time), 'Actions' (by idx/seq or op path), 'Commands' (toggle lens, toggle preset, export/import, copy permalink, promote effects). Each result has a right-aligned mode/lens glyph; Enter routes into the shared (path, cursor) URL state. Export/Import open a lightweight sub-panel: Export = include-toggles (merged action log · agui trace · overlay snapshot · mount manifest) + estimated size + Download; Import = drop zone → re-hydrate → 'replaying imported session — backing reconstruction deferred' banner.

**Key components.** FuzzyIndex (trajectory distinct paths + mounts + run list + command verbs); GroupedResults (Sources / Runs / Actions / Commands with glyphs; ↑↓ Enter Esc); ExportComposer (generalizes TrajectoryPage.exportJson to merged log + agui trace → .mirage-session.json); ImportDropzone (replayAguiEvents re-hydrate into read-only scrub; live tail disabled); ReplayBanner ('imported · scrub limited to overlay/reads/run; backing pinned-only'); IntegrityNote ('persisted' vs 'in-memory — trace may be empty after restart')

**Sample data (as rendered in the mockup).** Query 'users.jsonl' → Sources: '/database/tables/users/data.jsonl' (glyph: Data) ; Runs: (none) ; Actions: 'idx 88 read users/data.jsonl', 'idx 92 read users/data.jsonl'. Query ':312' → Actions: 'jump cursor to action 312'. Commands: 'Export session bundle (~1.8 MB: 419 actions + agui trace + overlay)', 'Toggle Data focus', 'Promote effects (1 pending: /rca_inc_5521.md)'. Export sub-panel: checkboxes [merged action log ✓ · agui_events trace ✓ · overlay snapshot ✓ · mount manifest ✓] · est 1.8 MB · Download 'session-northhill-incident-fc92.mirage-session.json'.

**Signature interaction.** Dev exports a session and sends the file to a teammate; the teammate drags it into Import, the action list and By-run/step tree fill, and they press Play to watch the run reconstruct. The Diff lens works on every VfsOp; the State Tree's backing node shows the 'pinned at stand-up' note instead of pretending to byte-rebuild the FS. Separately, the dev types ':88' in Cmd-K to jump the cursor straight to action 88 without touching the mouse.

---

## Appendix B — How this design differs from prior work

VS THE LEGACY console (Workspaces → Run → Trajectory → State → Promote, the routed SUB_NAV in today's ConsoleLayout): that was an OPS/GOVERNANCE product with a page-switcher mental model and a promote workflow as a front door. This reframe DELETES the page-switcher entirely — there are no routed pages, only one always-mounted organism where navigation is cursor movement + lens selection + layout preset. The five legacy pages are demoted to lenses/views over one cursor: Trajectory becomes the Action List + Time-Travel centerpiece; State becomes the State Tree lens (folded to the cursor, not a standalone browser); Run becomes the By-run/step grouping lens; Promote/Workspaces collapse to a quiet per-write effect-class dot + a Cmd-K-only promote — no pending-effects counter in the chrome, no LIVE red banner, no typed-PROMOTE modal. The container flips from a cross-session ops inbox to a single WORKSPACE whose home shows ALL traces + ALL events.

VS THE PRIOR TRACE-VIEWER design (the strong 'trace viewer + investigation/governance' research that preceded the pivot): that design's pillars were a single-run trace waterfall plus an 'Investigation evidence object' and a 'Workspaces build/promote' flow. This reframe keeps the still-valid bones — the single-run waterfall + correlated VfsOp ground-truth inspector (drift flag, latency-phase bars, click-to-cross-highlight), per-node permalinks, and a lighter Compare — but RE-RANKS everything around two NEW first-class pillars the prior design did not have: (1) the Redux-style Event Log + Time-Travel State Inspector (action list, state tree, exact per-action diff, jump/skip, future-dimming, import/export) as the centerpiece, and (2) a connected Data-Sources explorer with the bidirectional data↔trace bridge ('who touched this byte?'). The Investigation object and the build/promote flow drop from pillars to minor/optional. Crucially, the prior waterfall is no longer a destination PAGE — it is a grouping LENS over the same flat action stream and the same single cursor, so 'all traces' and 'one trace' are one surface, not two routes. And the honesty posture is sharper and code-verified: solid ground truth (the exact OpRecord diff, the exact mount_prefix+path bridge join) vs muted-and-labeled inferred/derived (timestamp merge with seq/§seq gutter, inferred op→step dot, derived cache chips) vs reserved-dimmed not-yet-emitted (lineage/policy/credential/PII rails, dead STATE_SNAPSHOT node, disabled query bar) — none of it faked, all of it mapped to real plumbing.

## Appendix C — Phased rollout (grounded in data feasibility)

1. Phase 0 (backend, highest-leverage, gates the 'exact' promises): stamp tool_call_id/step_id/run_id + restore the dropped source/duration_ms/fingerprint/revision onto every VfsOp at emission (server.py ~L1403); consume ExecutionNode.records instead of length-diffing ws.ops.records; fill vfs_ops.tool_call_id in the coalescer. This single fix upgrades the merged-stream ordering from timestamp-approximate to exact AND every op→step attribution from inferred to joined. In parallel, stand up arcadia_store-backed paginated/virtualized reads (the console watching ALL events cannot ride the 2000-event RAM ring) and add read methods for the currently WRITE-ONLY runs/steps/tool_calls/vfs_ops so post-restart history works.

2. Phase 1 — the spine on solid substrate: build the always-mounted shell (44px header + workspace switcher + persisted/in-memory pill + Cmd-K), the virtualized merged Action List with future-dimming and the seq/§seq gutter, the TransportBar with the draggable playhead, and the net-new stateAt(N) fold engine (trajectory[0..idx] over _console_overlay/_console_trajectory/_console_effects + replayAguiEvents sliced to the cursor). Ship the EXACT VfsOp Diff lens first (reuse OverlayDiff; action idx == OpRecord[idx]) — the moat move — plus the State Tree lens and the Action lens. Reuse exportJson; add Import. Default to Time-Travel focus.

3. Phase 2 — all-traces + data pillar + the bridge: add the dedicated All-Traces run-rail overview (Workbench graft) and wire lane→scope; add the Flat⇄By-run/step grouping lens + Trace lens (reuse RunTracePanel/StepCard/ToolCallRow). Promote the Data Pillar to first-class with the mount catalog (effect-class chips + touched-by rollups), the FILE-TREE skin (vfsList/vfsFile + honesty strip) and the TableCard skin (Schema/Rows/Stats over the real schema.json/data.jsonl/stats.json), the disabled query bar, and the reserved metadata strip. Ship the bidirectional bridge (Touched-by find-usages + cursor-jump + automatic inverse ring) and the Data-focus layout preset. Bake in the named wrong-file/stale-revision flow.

4. Phase 3 — polish, Compare, and honesty-label retirement (gated on Phase 0 landing): add the lighter Compare lens (dual cursor + first-divergence marker + file side-by-side) reusing BranchTree/StatePage code. Once Phase 0 is in, REMOVE the 'inferred order' timestamp-merge hairline and the 'inferred' op→step dots (now exact/joined) and light up the latency-phase attribution and any S3 drift flags from real fingerprint/revision. Keep every remaining honesty label that still maps to a real gap (backing pinned-at-stand-up, served-from-cache derived, preview-only on cat, reserved not-yet-emitted lineage/policy/credential/PII rails, disabled catalog-proxy query bar) — softening any of those turns truth into a lie. Governance stays demoted: promote remains Cmd-K-only.

## Appendix D — How this document was produced

This design was produced by two multi-agent workflows over the real `mirage` + Arcadia codebase: (1) a 15-agent research+design pass (7 parallel subsystem readers → consolidate/critique → 3 design paradigms → 3 judges → synthesis), then (2) — after the pivot to a *developer debug console* — a 9-agent focused redesign (2 fresh grounding readers on the new pillars → 3 dev-console paradigms → 3 judges → synthesis) that reused the prior grounding via `_reframe.md`. Every load-bearing claim (file paths, line numbers, what is shipped vs partial vs aspirational) was verified against the source. Research artifacts: `_reframe.md`, `_v2_final.json`, `_v2_designs.json`, `_v2_verdicts.json`, `_v2_grounding.json`.
