import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  CircleDot,
  GitFork,
  Loader2,
  Play,
  Plus,
  Server,
  Trash2,
  X,
} from "lucide-react";
import {
  branchWorkspace,
  createConsoleWorkspace,
  deleteConsoleWorkspace,
  standupDryRun,
  standupWorkspace,
} from "@/api/client";
import {
  loadConsoleWorkspaces,
  refreshWorkspaceDetail,
  setActiveWorkspace,
  upsertWorkspaceDetail,
  useConsoleStore,
} from "@/lib/consoleStore";
import { WORKSPACE_TEMPLATES } from "@/lib/workspaceTemplates";
import type { DryRunResult, MountSpec } from "@/types/console";
import { cn, timeAgo } from "@/lib/utils";
import {
  EffectClassTag,
  ModeBadge,
  MountConfigForm,
  ProvisionDryRun,
  WorkspaceYamlPreview,
} from "@/components/console";
import { Button } from "@/components/ui";

interface DraftForm {
  name: string;
  templateId: string;
  mounts: MountSpec[];
}

const STATUS_DOT: Record<string, string> = {
  created: "bg-text-faint",
  ready: "bg-success",
  error: "bg-danger",
};

export default function WorkspacesPage() {
  const store = useConsoleStore();
  const navigate = useNavigate();
  const [draft, setDraft] = useState<DraftForm | null>(null);
  const [creating, setCreating] = useState(false);
  const [dryRun, setDryRun] = useState<{
    wsId: string;
    result: DryRunResult;
  } | null>(null);
  const [standingUp, setStandingUp] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  function startTemplate(id: string) {
    const t = WORKSPACE_TEMPLATES.find((x) => x.id === id);
    if (!t) return;
    setDraft({
      name: t.title,
      templateId: t.id,
      mounts: t.mounts.map((m) => ({ path: m.path, mode: m.mode })),
    });
  }

  async function create() {
    if (!draft) return;
    setCreating(true);
    try {
      const detail = await createConsoleWorkspace({
        name: draft.name,
        template_id: draft.templateId,
        mounts: draft.mounts,
      });
      upsertWorkspaceDetail(detail);
      setActiveWorkspace(detail.id);
      setDraft(null);
      const dr = await standupDryRun(detail.id);
      setDryRun({ wsId: detail.id, result: dr });
    } finally {
      setCreating(false);
    }
  }

  async function openDryRun(wsId: string) {
    setBusyId(wsId);
    try {
      const dr = await standupDryRun(wsId);
      setDryRun({ wsId, result: dr });
    } finally {
      setBusyId(null);
    }
  }

  async function confirmStandup() {
    if (!dryRun) return;
    setStandingUp(true);
    try {
      const detail = await standupWorkspace(dryRun.wsId);
      upsertWorkspaceDetail(detail);
      setActiveWorkspace(detail.id);
      setDryRun(null);
      navigate("/console/run");
    } finally {
      setStandingUp(false);
    }
  }

  async function openWorkspace(wsId: string, ready: boolean) {
    setActiveWorkspace(wsId);
    if (ready) navigate("/console/run");
    else openDryRun(wsId);
  }

  async function doBranch(wsId: string) {
    setBusyId(wsId);
    try {
      const detail = await branchWorkspace(wsId);
      upsertWorkspaceDetail(detail);
      await loadConsoleWorkspaces();
    } finally {
      setBusyId(null);
    }
  }

  async function doDelete(wsId: string) {
    if (!window.confirm("Tear down this workspace?")) return;
    setBusyId(wsId);
    try {
      await deleteConsoleWorkspace(wsId);
      if (store.activeId === wsId) setActiveWorkspace(null);
      await loadConsoleWorkspaces();
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="scrollbar-thin h-full overflow-y-auto">
      <div className="mx-auto max-w-[1100px] px-6 py-6">
        <div className="mb-5">
          <h1 className="text-[16px] font-semibold tracking-tight">Workspaces</h1>
          <p className="mt-0.5 text-[12px] text-text-muted">
            Stand up a Mirage instance, run an agent against virtualized state,
            and decide what to commit to the real world.
          </p>
        </div>

        <section className="mb-7">
          <h2 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-text-faint">
            Start from a template
          </h2>
          <div className="grid grid-cols-2 gap-2.5 lg:grid-cols-3">
            {WORKSPACE_TEMPLATES.map((t) => (
              <button
                key={t.id}
                onClick={() => startTemplate(t.id)}
                className="group flex flex-col gap-1.5 rounded-xl border border-border bg-surface-1 p-3 text-left transition-colors hover:border-border-hover hover:bg-surface-2"
              >
                <div className="flex items-center gap-2">
                  <span className="grid h-7 w-7 place-items-center rounded-lg bg-accent-soft text-accent">
                    <Plus size={14} />
                  </span>
                  <span className="text-[13px] font-medium text-text-primary">
                    {t.title}
                  </span>
                </div>
                <p className="line-clamp-2 text-[11px] leading-snug text-text-muted">
                  {t.tagline}
                </p>
                <div className="mt-0.5 flex flex-wrap gap-1">
                  {t.mounts.slice(0, 4).map((m) => (
                    <span
                      key={m.path}
                      className="rounded bg-surface-3 px-1.5 py-0.5 font-mono text-[9px] text-text-muted"
                    >
                      {m.path}
                    </span>
                  ))}
                </div>
              </button>
            ))}
          </div>
        </section>

        <section>
          <h2 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-text-faint">
            Your workspaces
          </h2>
          {store.workspaces.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border py-10 text-center">
              <Server size={22} className="mx-auto mb-2 text-text-faint" />
              <p className="text-[12px] text-text-muted">
                No workspaces yet — start from a template above.
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {store.workspaces.map((w) => (
                <div
                  key={w.id}
                  className={cn(
                    "flex items-center gap-3 rounded-xl border bg-surface-1 px-3.5 py-3 transition-colors",
                    store.activeId === w.id
                      ? "border-accent/40"
                      : "border-border hover:border-border-hover",
                  )}
                >
                  <span
                    className={cn(
                      "h-2.5 w-2.5 shrink-0 rounded-full",
                      STATUS_DOT[w.status] ?? "bg-text-faint",
                    )}
                    title={w.status}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="truncate text-[13px] font-medium text-text-primary">
                        {w.name}
                      </span>
                      <ModeBadge mode={w.mode} size="sm" />
                      {w.parent_id && (
                        <span className="flex items-center gap-1 font-mono text-[10px] text-text-faint">
                          <GitFork size={10} /> {w.branch}
                        </span>
                      )}
                    </div>
                    <div className="mt-0.5 flex items-center gap-2 font-mono text-[10px] text-text-muted">
                      <span>{w.mount_count} mounts</span>
                      <span>·</span>
                      <span className="capitalize">{w.status}</span>
                      <span>·</span>
                      <span>{timeAgo(w.created_at * 1000)}</span>
                      {w.pending_effects > 0 && (
                        <span className="rounded bg-simulated-soft px-1.5 text-simulated">
                          {w.pending_effects} pending
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-1.5">
                    <Button
                      size="sm"
                      variant={w.status === "ready" ? "primary" : "secondary"}
                      onClick={() => openWorkspace(w.id, w.status === "ready")}
                      disabled={busyId === w.id}
                    >
                      {busyId === w.id ? (
                        <Loader2 size={13} className="animate-spin" />
                      ) : w.status === "ready" ? (
                        <Play size={13} />
                      ) : (
                        <Server size={13} />
                      )}
                      {w.status === "ready" ? "Open" : "Stand up"}
                    </Button>
                    <button
                      onClick={() => doBranch(w.id)}
                      disabled={busyId === w.id || w.status !== "ready"}
                      title="Branch"
                      className="grid h-8 w-8 place-items-center rounded-lg text-text-muted transition-colors hover:bg-surface-3 hover:text-text-primary disabled:opacity-40"
                    >
                      <GitFork size={14} />
                    </button>
                    <button
                      onClick={() => doDelete(w.id)}
                      disabled={busyId === w.id}
                      title="Tear down"
                      className="grid h-8 w-8 place-items-center rounded-lg text-text-muted transition-colors hover:bg-surface-3 hover:text-danger disabled:opacity-40"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      {draft && (
        <CreateModal
          draft={draft}
          setDraft={setDraft}
          onClose={() => setDraft(null)}
          onCreate={create}
          creating={creating}
        />
      )}

      {dryRun && (
        <StandupModal
          result={dryRun.result}
          onCancel={() => setDryRun(null)}
          onConfirm={confirmStandup}
          standingUp={standingUp}
        />
      )}
    </div>
  );
}

function CreateModal({
  draft,
  setDraft,
  onClose,
  onCreate,
  creating,
}: {
  draft: DraftForm;
  setDraft: (d: DraftForm) => void;
  onClose: () => void;
  onCreate: () => void;
  creating: boolean;
}) {
  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="flex max-h-[88vh] w-full max-w-3xl flex-col overflow-hidden rounded-xl border border-border bg-surface-1 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2.5 border-b border-border px-4 py-3">
          <CircleDot size={15} className="text-accent" />
          <h2 className="text-[13px] font-semibold">Configure workspace</h2>
          <button
            onClick={onClose}
            className="ml-auto grid h-7 w-7 place-items-center rounded-md text-text-muted hover:bg-surface-3 hover:text-text-primary"
          >
            <X size={15} />
          </button>
        </div>
        <div className="grid min-h-0 flex-1 grid-cols-2 gap-4 overflow-y-auto p-4">
          <div className="flex flex-col gap-3">
            <div>
              <label className="mb-1 block text-[11px] text-text-muted">Name</label>
              <input
                value={draft.name}
                onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                className="w-full rounded-lg border border-border bg-surface-0 px-3 py-2 text-[13px] text-text-primary outline-none focus-visible:border-accent"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-[11px] text-text-muted">
                Mounts
              </label>
              <MountConfigForm
                mounts={draft.mounts}
                onChange={(mounts) => setDraft({ ...draft, mounts })}
              />
            </div>
          </div>
          <div className="flex min-h-0 flex-col">
            <label className="mb-1.5 block text-[11px] text-text-muted">
              workspace.yaml
            </label>
            <WorkspaceYamlPreview
              name={draft.name}
              templateId={draft.templateId}
              mode="TEST"
              mounts={draft.mounts}
            />
          </div>
        </div>
        <div className="flex items-center justify-end gap-2 border-t border-border px-4 py-3">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" onClick={onCreate} disabled={creating}>
            {creating ? (
              <Loader2 size={13} className="animate-spin" />
            ) : (
              <Server size={13} />
            )}
            Create &amp; configure stand-up
          </Button>
        </div>
      </div>
    </div>
  );
}

function StandupModal({
  result,
  onCancel,
  onConfirm,
  standingUp,
}: {
  result: DryRunResult;
  onCancel: () => void;
  onConfirm: () => void;
  standingUp: boolean;
}) {
  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
      onClick={onCancel}
    >
      <div
        className="w-full max-w-2xl overflow-hidden rounded-xl border border-border bg-surface-1 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2.5 border-b border-border px-4 py-3">
          <Server size={15} className="text-accent" />
          <h2 className="text-[13px] font-semibold">Stand up — provision dry-run</h2>
          <button
            onClick={onCancel}
            className="ml-auto grid h-7 w-7 place-items-center rounded-md text-text-muted hover:bg-surface-3 hover:text-text-primary"
          >
            <X size={15} />
          </button>
        </div>
        <div className="max-h-[60vh] overflow-y-auto p-4">
          <ProvisionDryRun result={result} />
          <p className="mt-3 text-[11px] text-text-faint">
            On confirm, every mount is connected and its backing state is pinned
            (snapshotted) so runs are reproducible and resettable.
          </p>
        </div>
        <div className="flex items-center justify-end gap-2 border-t border-border px-4 py-3">
          <Button variant="ghost" onClick={onCancel} disabled={standingUp}>
            Cancel
          </Button>
          <Button variant="primary" onClick={onConfirm} disabled={standingUp}>
            {standingUp ? (
              <Loader2 size={13} className="animate-spin" />
            ) : (
              <Server size={13} />
            )}
            Connect &amp; pin backing
          </Button>
        </div>
      </div>
    </div>
  );
}
