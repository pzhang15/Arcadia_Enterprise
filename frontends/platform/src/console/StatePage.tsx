import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Camera,
  ChevronRight,
  File as FileIcon,
  Folder,
  GitFork,
  Loader2,
  RotateCcw,
  Layers,
} from "lucide-react";
import {
  branchWorkspace,
  createConsoleSession,
  getOverlay,
  resetWorkspace,
  snapshotWorkspace,
  vfsFile,
  vfsList,
} from "@/api/client";
import {
  loadConsoleWorkspaces,
  refreshWorkspaceDetail,
  selectActiveDetail,
  setActiveWorkspace,
  upsertWorkspaceDetail,
  useConsoleStore,
} from "@/lib/consoleStore";
import type { OverlayDiff as OverlayDiffData } from "@/types/console";
import { cn, formatBytes } from "@/lib/utils";
import { mountBgClass } from "@/lib/mountColor";
import { BranchTree, OverlayDiff } from "@/components/console";
import { Button, SegmentedControl } from "@/components/ui";
import { NoWorkspace } from "./NoWorkspace";

type Layer = "effective" | "overlay" | "backing";

interface Entry {
  name: string;
  type: "dir" | "file";
  size?: number;
}

export default function StatePage() {
  const store = useConsoleStore();
  const active = selectActiveDetail(store);
  const activeId = active?.id ?? null;

  const [overlay, setOverlay] = useState<OverlayDiffData>({ mounts: [] });
  const [layer, setLayer] = useState<Layer>("overlay");
  const [selectedMount, setSelectedMount] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [cwd, setCwd] = useState("/");
  const [entries, setEntries] = useState<Entry[]>([]);
  const [fileContent, setFileContent] = useState<{ path: string; content: string } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const refreshOverlay = useCallback(() => {
    if (!activeId) return;
    getOverlay(activeId).then(setOverlay).catch(() => {});
  }, [activeId]);

  useEffect(() => {
    setSessionId(null);
    setFileContent(null);
    setCwd("/");
    setSelectedMount(null);
    refreshOverlay();
  }, [activeId, refreshOverlay]);

  useEffect(() => {
    refreshOverlay();
  }, [active?.pending_effects, refreshOverlay]);

  useEffect(() => {
    if (active?.status === "ready" && !sessionId) {
      createConsoleSession(active.id)
        .then((s) => setSessionId(s.id))
        .catch(() => {});
    }
  }, [active?.status, active?.id, sessionId]);

  const browseRoot = selectedMount ?? "/";
  useEffect(() => {
    if (layer === "overlay" || !sessionId) return;
    vfsList(sessionId, cwd)
      .then((r) => setEntries(r.entries))
      .catch(() => setEntries([]));
  }, [sessionId, cwd, layer]);

  useEffect(() => {
    setCwd(browseRoot);
    setFileContent(null);
  }, [browseRoot, layer]);

  const changedPaths = useMemo(() => {
    const s = new Set<string>();
    for (const m of overlay.mounts) for (const c of m.changes) s.add(c.path);
    return s;
  }, [overlay]);

  if (!active) return <NoWorkspace />;

  async function openEntry(e: Entry) {
    if (!sessionId) return;
    const next = cwd.endsWith("/") ? `${cwd}${e.name}` : `${cwd}/${e.name}`;
    if (e.type === "dir") {
      setCwd(next);
      setFileContent(null);
    } else {
      const f = await vfsFile(sessionId, next);
      setFileContent({ path: next, content: f.content });
    }
  }

  async function doSnapshot() {
    if (!activeId) return;
    const name = window.prompt(
      "Snapshot name",
      `snap-${(active?.snapshots.length ?? 0) + 1}`,
    );
    if (!name) return;
    setBusy("snap");
    try {
      await snapshotWorkspace(activeId, name);
      await refreshWorkspaceDetail(activeId);
    } finally {
      setBusy(null);
    }
  }

  async function doBranch() {
    if (!activeId) return;
    setBusy("branch");
    try {
      const detail = await branchWorkspace(activeId);
      upsertWorkspaceDetail(detail);
      await loadConsoleWorkspaces();
      setActiveWorkspace(detail.id);
    } finally {
      setBusy(null);
    }
  }

  async function doReset() {
    if (!activeId) return;
    if (!window.confirm("Discard the overlay and return the world to pristine backing state?"))
      return;
    setBusy("reset");
    try {
      const detail = await resetWorkspace(activeId);
      upsertWorkspaceDetail(detail);
      setSessionId(null);
      setFileContent(null);
      refreshOverlay();
    } finally {
      setBusy(null);
    }
  }

  const totalChanges = overlay.mounts.reduce((n, m) => n + m.changes.length, 0);

  return (
    <div className="flex h-full min-h-0">
      <aside className="flex w-[240px] shrink-0 flex-col border-r border-border bg-surface-0">
        <div className="border-b border-border px-3 py-2.5">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-text-faint">
              Mounts
            </span>
            <span className="font-mono text-[10px] text-text-muted tabular-nums">
              +{totalChanges}
            </span>
          </div>
          <button
            onClick={() => setSelectedMount(null)}
            className={cn(
              "mb-0.5 flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-[12px] transition-colors",
              selectedMount === null
                ? "bg-accent-soft text-accent"
                : "text-text-secondary hover:bg-surface-2",
            )}
          >
            <Layers size={13} /> All mounts
          </button>
          {active.mounts.map((m) => {
            const changes =
              overlay.mounts.find((x) => x.prefix === m.prefix)?.changes.length ?? 0;
            return (
              <button
                key={m.prefix}
                onClick={() => setSelectedMount(m.prefix)}
                className={cn(
                  "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left transition-colors",
                  selectedMount === m.prefix
                    ? "bg-accent-soft"
                    : "hover:bg-surface-2",
                )}
              >
                <span className={cn("h-2 w-2 shrink-0 rounded-full", mountBgClass(m.prefix))} />
                <span className="truncate font-mono text-[11px] text-text-secondary">
                  {m.prefix}
                </span>
                {changes > 0 && (
                  <span className="ml-auto rounded bg-captured-soft px-1 font-mono text-[9px] text-captured tabular-nums">
                    +{changes}
                  </span>
                )}
              </button>
            );
          })}
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-3 py-2.5">
          <span className="mb-2 block text-[11px] font-semibold uppercase tracking-wide text-text-faint">
            Branch tree
          </span>
          <BranchTree
            workspaces={store.workspaces}
            activeId={activeId}
            onSelect={(id) => setActiveWorkspace(id)}
          />
        </div>
      </aside>

      <div className="flex min-h-0 flex-1 flex-col">
        <div className="flex shrink-0 items-center gap-2 border-b border-border bg-surface-0 px-3 py-2">
          <SegmentedControl<Layer>
            size="sm"
            value={layer}
            onChange={setLayer}
            options={[
              { id: "backing", label: "Backing" },
              { id: "overlay", label: "Overlay", count: totalChanges },
              { id: "effective", label: "Effective" },
            ]}
          />
          <div className="ml-auto flex items-center gap-1.5">
            <Button size="sm" variant="secondary" onClick={doSnapshot} disabled={busy !== null}>
              {busy === "snap" ? <Loader2 size={13} className="animate-spin" /> : <Camera size={13} />}
              Snapshot
            </Button>
            <Button size="sm" variant="secondary" onClick={doBranch} disabled={busy !== null}>
              {busy === "branch" ? <Loader2 size={13} className="animate-spin" /> : <GitFork size={13} />}
              Branch
            </Button>
            <Button size="sm" variant="danger" onClick={doReset} disabled={busy !== null}>
              {busy === "reset" ? <Loader2 size={13} className="animate-spin" /> : <RotateCcw size={13} />}
              Reset
            </Button>
          </div>
        </div>

        {layer === "overlay" ? (
          <div className="min-h-0 flex-1">
            <OverlayDiff overlay={overlay} selectedPrefix={selectedMount} />
          </div>
        ) : (
          <div className="grid min-h-0 flex-1 grid-cols-[1fr_1fr]">
            <div className="flex min-h-0 flex-col border-r border-border">
              {layer === "backing" && (
                <div className="shrink-0 border-b border-border bg-surface-1 px-3 py-1.5 text-[10px] text-text-faint">
                  Pinned at stand-up. Read-only mounts equal backing; pre-overlay
                  reconstruction of written mounts is a Replay feature (deferred).
                </div>
              )}
              <div className="flex shrink-0 items-center gap-1 overflow-x-auto border-b border-border px-3 py-1.5 font-mono text-[11px] text-text-muted">
                {cwd.split("/").filter(Boolean).length === 0 ? (
                  <span className="text-text-secondary">/</span>
                ) : (
                  <>
                    <button onClick={() => setCwd("/")} className="hover:text-text-primary">
                      /
                    </button>
                    {cwd
                      .split("/")
                      .filter(Boolean)
                      .map((seg, i, arr) => {
                        const p = "/" + arr.slice(0, i + 1).join("/");
                        return (
                          <span key={p} className="flex items-center gap-1">
                            <ChevronRight size={11} className="text-text-faint" />
                            <button onClick={() => setCwd(p)} className="hover:text-text-primary">
                              {seg}
                            </button>
                          </span>
                        );
                      })}
                  </>
                )}
              </div>
              <div className="scrollbar-thin min-h-0 flex-1 overflow-y-auto p-1.5">
                {entries.length === 0 ? (
                  <p className="px-2 py-6 text-center text-[11px] text-text-faint">
                    {sessionId ? "Empty." : "Connecting…"}
                  </p>
                ) : (
                  entries.map((e) => {
                    const full = cwd.endsWith("/") ? `${cwd}${e.name}` : `${cwd}/${e.name}`;
                    const changed = changedPaths.has(full);
                    return (
                      <button
                        key={e.name}
                        onClick={() => openEntry(e)}
                        className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left transition-colors hover:bg-surface-2"
                      >
                        {e.type === "dir" ? (
                          <Folder size={13} className="shrink-0 text-info" />
                        ) : (
                          <FileIcon size={13} className="shrink-0 text-text-muted" />
                        )}
                        <span className="truncate font-mono text-[11px] text-text-secondary">
                          {e.name}
                        </span>
                        {changed && (
                          <span className="ml-auto h-1.5 w-1.5 shrink-0 rounded-full bg-captured" title="changed in overlay" />
                        )}
                        {e.size !== undefined && e.type === "file" && (
                          <span className={cn("font-mono text-[10px] text-text-faint tabular-nums", changed ? "" : "ml-auto")}>
                            {formatBytes(e.size)}
                          </span>
                        )}
                      </button>
                    );
                  })
                )}
              </div>
            </div>
            <div className="min-h-0 overflow-hidden bg-surface-0">
              {fileContent ? (
                <div className="flex h-full flex-col">
                  <div className="shrink-0 border-b border-border px-3 py-1.5">
                    <span className="font-mono text-[11px] text-text-secondary">
                      {fileContent.path}
                    </span>
                  </div>
                  <pre className="scrollbar-thin min-h-0 flex-1 overflow-auto p-3 font-mono text-[11px] leading-relaxed text-text-secondary">
                    {fileContent.content}
                  </pre>
                </div>
              ) : (
                <div className="flex h-full items-center justify-center px-6 text-center text-[11px] text-text-faint">
                  Select a file to view its {layer} content.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
