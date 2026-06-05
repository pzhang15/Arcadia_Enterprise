import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useOutletContext } from "react-router-dom";
import {
  ArrowDownToLine,
  Download,
  PlayCircle,
  RefreshCw,
  Search,
} from "lucide-react";
import { getConsoleFile, getTrajectory } from "@/api/client";
import { selectActiveDetail, useConsoleStore } from "@/lib/consoleStore";
import type { CaptureState, TrajectoryEntry, TrajectoryKind } from "@/types/console";
import { cn, formatBytes, formatTime } from "@/lib/utils";
import { mountBgClass } from "@/lib/mountColor";
import { CaptureBadge, EffectClassTag } from "@/components/console";
import { Button, SegmentedControl } from "@/components/ui";
import type { ConsoleOutletCtx } from "./ConsoleLayout";
import { NoWorkspace } from "./NoWorkspace";

const CAPTURE_FILTERS: { id: CaptureState | "all"; label: string }[] = [
  { id: "all", label: "All" },
  { id: "captured", label: "Captured" },
  { id: "simulated", label: "Simulated" },
  { id: "live", label: "Live" },
];

export default function TrajectoryPage() {
  const { events } = useOutletContext<ConsoleOutletCtx>();
  const store = useConsoleStore();
  const active = selectActiveDetail(store);
  const activeId = active?.id ?? null;

  const [entries, setEntries] = useState<TrajectoryEntry[]>([]);
  const [kind, setKind] = useState<TrajectoryKind | "all">("all");
  const [capture, setCapture] = useState<CaptureState | "all">("all");
  const [mount, setMount] = useState<string>("all");
  const [query, setQuery] = useState("");
  const [expanded, setExpanded] = useState<number | null>(null);
  const [preview, setPreview] = useState<{ idx: number; content: string } | null>(null);
  const lastFetch = useRef(0);

  const refresh = useCallback(() => {
    if (!activeId) return;
    lastFetch.current = Date.now();
    getTrajectory(activeId)
      .then((r) => setEntries(r.entries))
      .catch(() => {});
  }, [activeId]);

  useEffect(() => {
    setEntries([]);
    setExpanded(null);
    setPreview(null);
    refresh();
  }, [activeId, refresh]);

  useEffect(() => {
    if (Date.now() - lastFetch.current > 700) refresh();
  }, [events.length, refresh]);

  const filtered = useMemo(() => {
    return entries.filter((e) => {
      if (kind !== "all" && e.kind !== kind) return false;
      if (capture !== "all" && e.capture_state !== capture) return false;
      if (mount !== "all" && e.mount_prefix !== mount) return false;
      if (query && !e.path.toLowerCase().includes(query.toLowerCase())) return false;
      return true;
    });
  }, [entries, kind, capture, mount, query]);

  const stats = useMemo(() => {
    let reads = 0;
    let writes = 0;
    let captured = 0;
    let simulated = 0;
    for (const e of entries) {
      if (e.kind === "read") reads++;
      if (e.kind === "write") writes++;
      if (e.capture_state === "captured") captured++;
      if (e.capture_state === "simulated") simulated++;
    }
    return { reads, writes, captured, simulated };
  }, [entries]);

  if (!active) return <NoWorkspace />;

  async function toggle(e: TrajectoryEntry) {
    if (expanded === e.idx) {
      setExpanded(null);
      return;
    }
    setExpanded(e.idx);
    setPreview(null);
    if (activeId && (e.kind === "read" || e.kind === "write")) {
      try {
        const f = await getConsoleFile(activeId, e.path);
        setPreview({ idx: e.idx, content: f.content.slice(0, 4000) });
      } catch {
        /* directory or unreadable */
      }
    }
  }

  function exportJson() {
    const blob = new Blob([JSON.stringify({ workspace: active!.name, entries }, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `trajectory-${active!.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex shrink-0 flex-wrap items-center gap-2 border-b border-border bg-surface-0 px-3 py-2">
        <SegmentedControl<TrajectoryKind | "all">
          size="sm"
          value={kind}
          onChange={setKind}
          options={[
            { id: "all", label: "All ops" },
            { id: "read", label: "Reads", count: stats.reads },
            { id: "write", label: "Writes", count: stats.writes },
          ]}
        />
        <div className="flex items-center gap-0.5 rounded-lg border border-border bg-surface-2 p-0.5">
          {CAPTURE_FILTERS.map((f) => (
            <button
              key={f.id}
              onClick={() => setCapture(f.id)}
              className={cn(
                "rounded-md px-2 py-1 text-[11px] font-medium transition-colors",
                capture === f.id
                  ? "bg-surface-4 text-text-primary"
                  : "text-text-muted hover:text-text-secondary",
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
        <select
          value={mount}
          onChange={(e) => setMount(e.target.value)}
          className="h-7 rounded-md border border-border bg-surface-2 pl-2.5 pr-7 text-[11px] text-text-secondary outline-none"
        >
          <option value="all">All mounts</option>
          {active.mounts.map((m) => (
            <option key={m.prefix} value={m.prefix}>
              {m.prefix}
            </option>
          ))}
        </select>
        <div className="relative">
          <Search size={13} className="absolute left-2 top-1/2 -translate-y-1/2 text-text-faint" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="filter path…"
            className="h-7 w-40 rounded-md border border-border bg-surface-0 pl-7 pr-2 font-mono text-[11px] text-text-primary outline-none focus-visible:border-accent"
          />
        </div>
        <div className="ml-auto flex items-center gap-1.5">
          <Button
            size="sm"
            variant="ghost"
            disabled
            title="Re-drive the run against the pinned snapshot (deferred — needs read-from-pin wiring)"
          >
            <PlayCircle size={13} /> Replay
          </Button>
          <Button size="sm" variant="ghost" onClick={refresh}>
            <RefreshCw size={13} />
          </Button>
          <Button size="sm" variant="secondary" onClick={exportJson}>
            <Download size={13} /> Export
          </Button>
        </div>
      </div>

      <div className="scrollbar-thin min-h-0 flex-1 overflow-y-auto">
        {filtered.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
            <ArrowDownToLine size={22} className="text-text-faint" />
            <p className="text-[12px] text-text-muted">No interactions yet.</p>
            <p className="max-w-[260px] text-[11px] text-text-faint">
              The unified, ordered record of everything the agent reads, captures,
              and simulates appears here as it runs.
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-border/50 font-mono text-[11px]">
            {filtered.map((e) => (
              <li key={e.idx}>
                <button
                  onClick={() => toggle(e)}
                  className={cn(
                    "flex w-full items-center gap-2.5 px-3 py-1.5 text-left transition-colors hover:bg-surface-1",
                    expanded === e.idx && "bg-surface-1",
                  )}
                >
                  <span className="w-16 shrink-0 text-text-faint tabular-nums">
                    {formatTime(e.timestamp)}
                  </span>
                  <span className={cn("h-2 w-2 shrink-0 rounded-full", mountBgClass(e.mount_prefix))} />
                  <span className="w-14 shrink-0 uppercase text-text-muted">{e.op}</span>
                  <span className="min-w-0 flex-1 truncate text-text-secondary">{e.path}</span>
                  {e.capture_state ? (
                    <CaptureBadge state={e.capture_state} size="xs" />
                  ) : (
                    <span className="shrink-0 rounded bg-surface-3 px-1.5 py-0.5 text-[9px] uppercase text-text-faint">
                      observed
                    </span>
                  )}
                  <span className="w-14 shrink-0 text-right text-text-faint tabular-nums">
                    {formatBytes(e.bytes || 0)}
                  </span>
                </button>
                {expanded === e.idx && (
                  <div className="border-t border-border/50 bg-surface-0 px-3 py-2.5">
                    <div className="mb-2 flex flex-wrap items-center gap-3 text-[10px] text-text-muted">
                      <span>source <span className="text-text-secondary">{e.source}</span></span>
                      <span>mount <span className="text-text-secondary">{e.mount_prefix}</span></span>
                      <span>{e.duration_ms}ms</span>
                      <EffectClassTag effectClass={e.effect_class} />
                    </div>
                    {preview && preview.idx === e.idx ? (
                      <pre className="scrollbar-thin max-h-52 overflow-auto rounded-md border border-border bg-surface-1 p-2 text-[10.5px] leading-relaxed text-text-secondary">
                        {preview.content || "(empty)"}
                      </pre>
                    ) : (
                      <p className="text-[10px] text-text-faint">
                        {e.kind === "meta" ? "Metadata op — no payload." : "No preview available."}
                      </p>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="flex shrink-0 items-center gap-3 border-t border-border bg-surface-0 px-3 py-1.5 font-mono text-[10px] text-text-muted">
        <span>{entries.length} ops</span>
        <span>·</span>
        <span className="text-captured">{stats.captured} captured</span>
        <span className="text-simulated">{stats.simulated} simulated</span>
        <span className="ml-auto">showing {filtered.length}</span>
      </div>
    </div>
  );
}
