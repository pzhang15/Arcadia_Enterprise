import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CheckSquare,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  Send,
  Square,
  Undo2,
} from "lucide-react";
import { getConsoleFile, getEffects, promoteEffects } from "@/api/client";
import {
  refreshWorkspaceDetail,
  selectActiveDetail,
  useConsoleStore,
} from "@/lib/consoleStore";
import {
  EFFECT_CLASS_ORDER,
  type EffectClass,
  type PendingEffect,
} from "@/types/console";
import { cn, formatBytes } from "@/lib/utils";
import { mountBgClass } from "@/lib/mountColor";
import { EFFECT_META } from "@/lib/captureState";
import {
  CaptureBadge,
  EffectClassTag,
  PromoteConfirmModal,
} from "@/components/console";
import { Button } from "@/components/ui";
import { NoWorkspace } from "./NoWorkspace";

function actionText(e: PendingEffect): string {
  switch (e.effect_class) {
    case "external-effect":
      return `Send to ${e.mount_prefix} — ${e.path}`;
    case "system-of-record":
      return `Commit record change at ${e.path}`;
    case "durable-internal":
      return `Apply durable write to ${e.path}`;
    default:
      return `Flush scratch file ${e.path}`;
  }
}

export default function PromotePage() {
  const store = useConsoleStore();
  const active = selectActiveDetail(store);
  const activeId = active?.id ?? null;

  const [effects, setEffects] = useState<PendingEffect[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [expanded, setExpanded] = useState<string | null>(null);
  const [previews, setPreviews] = useState<Record<string, string>>({});
  const [modalOpen, setModalOpen] = useState(false);
  const [committing, setCommitting] = useState(false);

  const refresh = useCallback(() => {
    if (!activeId) return;
    getEffects(activeId)
      .then((r) => setEffects(r.effects))
      .catch(() => {});
  }, [activeId]);

  useEffect(() => {
    setSelected(new Set());
    setExpanded(null);
    refresh();
  }, [activeId, active?.pending_effects, refresh]);

  const groups = useMemo(() => {
    const m = new Map<string, PendingEffect[]>();
    for (const e of effects) {
      const arr = m.get(e.mount_prefix) ?? [];
      arr.push(e);
      m.set(e.mount_prefix, arr);
    }
    for (const arr of m.values()) {
      arr.sort(
        (a, b) =>
          EFFECT_CLASS_ORDER.indexOf(a.effect_class) -
          EFFECT_CLASS_ORDER.indexOf(b.effect_class),
      );
    }
    return [...m.entries()];
  }, [effects]);

  const pending = useMemo(() => effects.filter((e) => !e.promoted), [effects]);
  const selectedEffects = useMemo(
    () => effects.filter((e) => selected.has(e.key)),
    [effects, selected],
  );

  if (!active) return <NoWorkspace />;

  function toggleOne(key: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function toggleAll() {
    if (selected.size === pending.length) setSelected(new Set());
    else setSelected(new Set(pending.map((e) => e.key)));
  }

  async function expand(e: PendingEffect) {
    if (expanded === e.key) {
      setExpanded(null);
      return;
    }
    setExpanded(e.key);
    if (activeId && !previews[e.key]) {
      try {
        const f = await getConsoleFile(activeId, e.path);
        setPreviews((p) => ({ ...p, [e.key]: f.content.slice(0, 4000) }));
      } catch {
        /* unreadable */
      }
    }
  }

  async function confirmPromote() {
    if (!activeId) return;
    setCommitting(true);
    try {
      await promoteEffects(activeId, [...selected]);
      await refreshWorkspaceDetail(activeId);
      setSelected(new Set());
      setModalOpen(false);
      refresh();
    } finally {
      setCommitting(false);
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex shrink-0 items-center gap-2 border-b border-border bg-surface-0 px-3 py-2">
        <button
          onClick={toggleAll}
          disabled={pending.length === 0}
          className="flex items-center gap-1.5 rounded-md px-2 py-1 text-[12px] text-text-secondary transition-colors hover:bg-surface-2 disabled:opacity-40"
        >
          {selected.size === pending.length && pending.length > 0 ? (
            <CheckSquare size={14} className="text-accent" />
          ) : (
            <Square size={14} />
          )}
          Select all
        </button>
        <span className="font-mono text-[11px] text-text-muted">
          {pending.length} pending · {effects.length - pending.length} promoted
        </span>
        <div className="ml-auto flex items-center gap-1.5">
          <Button
            size="sm"
            variant="ghost"
            disabled
            title="Compensating actions to unwind committed effects (engine support deferred)"
          >
            <Undo2 size={13} /> Unwind
          </Button>
          <Button size="sm" variant="ghost" onClick={refresh}>
            <RefreshCw size={13} />
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => setModalOpen(true)}
            disabled={selected.size === 0}
            className="!bg-live hover:!bg-live-strong"
          >
            <Send size={13} /> Promote {selected.size > 0 ? selected.size : ""}
          </Button>
        </div>
      </div>

      <div className="scrollbar-thin min-h-0 flex-1 overflow-y-auto p-3">
        {effects.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
            <Send size={22} className="text-text-faint" />
            <p className="text-[12px] text-text-muted">No captured effects to review.</p>
            <p className="max-w-[280px] text-[11px] text-text-faint">
              Run an agent that writes. Every captured write and simulated effect
              shows up here for deliberate, governed promotion.
            </p>
          </div>
        ) : (
          <div className="mx-auto flex max-w-[920px] flex-col gap-3">
            <div className="flex items-start gap-2 rounded-lg border border-simulated/40 bg-simulated-soft px-3 py-2">
              <CaptureBadge state="simulated" size="xs" />
              <p className="text-[11px] leading-snug text-text-muted">
                Promotion is the only path from captured to real. In this build the
                commit is <span className="font-semibold text-simulated">simulated</span> — effects are marked
                promoted and logged, but no real external calls are made yet.
              </p>
            </div>

            {groups.map(([prefix, items]) => (
              <div
                key={prefix}
                className="overflow-hidden rounded-xl border border-border bg-surface-1"
              >
                <div className="flex items-center gap-2 border-b border-border bg-surface-1 px-3 py-2">
                  <span className={cn("h-2.5 w-2.5 shrink-0 rounded-full", mountBgClass(prefix))} />
                  <span className="font-mono text-[12px] text-text-primary">{prefix}</span>
                  <span className="font-mono text-[10px] text-text-faint">
                    {items.length} effect{items.length === 1 ? "" : "s"}
                  </span>
                </div>
                <ul className="divide-y divide-border/50">
                  {items.map((e) => {
                    const meta = EFFECT_META[e.effect_class];
                    return (
                      <li key={e.key}>
                        <div
                          className={cn(
                            "flex items-center gap-2.5 px-3 py-2",
                            e.promoted && "opacity-60",
                          )}
                        >
                          <button
                            onClick={() => !e.promoted && toggleOne(e.key)}
                            disabled={e.promoted}
                            className="shrink-0"
                          >
                            {e.promoted ? (
                              <CheckSquare size={15} className="text-live" />
                            ) : selected.has(e.key) ? (
                              <CheckSquare size={15} className="text-accent" />
                            ) : (
                              <Square size={15} className="text-text-muted" />
                            )}
                          </button>
                          <button
                            onClick={() => expand(e)}
                            className="flex min-w-0 flex-1 items-center gap-2 text-left"
                          >
                            {expanded === e.key ? (
                              <ChevronDown size={13} className="shrink-0 text-text-faint" />
                            ) : (
                              <ChevronRight size={13} className="shrink-0 text-text-faint" />
                            )}
                            <span className="min-w-0 flex-1">
                              <span className="block truncate text-[12px] text-text-primary">
                                {actionText(e)}
                              </span>
                              <span className="block truncate text-[10px] text-text-faint">
                                {meta.label} · {e.reversibility}
                              </span>
                            </span>
                          </button>
                          <EffectClassTag effectClass={e.effect_class} />
                          <CaptureBadge state={e.capture_state} size="xs" flash={e.promoted} />
                          <span className="w-12 shrink-0 text-right font-mono text-[10px] text-text-faint tabular-nums">
                            {formatBytes(e.bytes || 0)}
                          </span>
                        </div>
                        {expanded === e.key && (
                          <div className="border-t border-border/50 bg-surface-0 px-3 py-2.5 pl-10">
                            <div className="mb-1.5 font-mono text-[10px] text-text-muted">
                              {e.op} · {e.path}
                            </div>
                            <pre className="scrollbar-thin max-h-52 overflow-auto rounded-md border border-border bg-surface-1 p-2 font-mono text-[10.5px] leading-relaxed text-text-secondary">
                              {previews[e.key] ?? "(loading preview…)"}
                            </pre>
                          </div>
                        )}
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))}
          </div>
        )}
      </div>

      <PromoteConfirmModal
        open={modalOpen}
        effects={selectedEffects}
        onConfirm={confirmPromote}
        onCancel={() => setModalOpen(false)}
        committing={committing}
      />
    </div>
  );
}
