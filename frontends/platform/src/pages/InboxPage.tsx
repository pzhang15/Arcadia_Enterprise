import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  ClipboardList,
  Clock,
  Hand,
  Loader2,
  Search,
  Send,
} from "lucide-react";
import { listSessions } from "@/api/client";
import { cn, timeAgo } from "@/lib/utils";
import {
  Badge,
  EmptyState,
  SectionLabel,
  SegmentedControl,
  StatCard,
} from "@/components/ui";
import {
  SEVERITY_ORDER,
  STATUS_ORDER,
  type InvestigationMeta,
  type InvestigationSeverity,
  type InvestigationStatus,
} from "@/types/investigation";
import { findTemplate } from "@/lib/workspaceTemplates";
import {
  useInvestigations,
  upsertInvestigation,
} from "@/lib/investigationStore";
import {
  SeverityBadge,
  StatusBadge,
  TriggerBadge,
} from "@/components/investigation/InvestigationBadges";

interface SessionRow {
  id: string;
  status: string;
  services: string[];
  created_at: number;
  message_count: number;
  last_message: string;
}

type StatusFilter = "all" | "active" | "needs_review" | "resolved";

// Derive an investigation status from a persisted session's real state, so
// idle/finished sessions are not mislabelled as actively "running".
function statusForSession(row: SessionRow): InvestigationStatus {
  if (row.status === "running") return "running";
  if (row.status === "error") return "needs_review";
  return row.message_count > 0 ? "needs_review" : "queued";
}

export default function InboxPage() {
  const navigate = useNavigate();
  const investigations = useInvestigations();
  const [sessions, setSessions] = useState<SessionRow[]>([]);
  const [filter, setFilter] = useState<StatusFilter>("all");
  const [severityFilter, setSeverityFilter] = useState<InvestigationSeverity | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    listSessions()
      .then((rows) => {
        if (cancelled) return;
        setSessions(rows);
        for (const row of rows) {
          if (!investigations[row.id]) {
            upsertInvestigation({
              sessionId: row.id,
              title: row.last_message || `Investigation ${row.id}`,
              status: statusForSession(row),
            });
          }
        }
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const enriched = useMemo<EnrichedRow[]>(() => {
    const bySessionId = new Map<string, EnrichedRow>();
    for (const s of sessions) {
      const meta = investigations[s.id];
      bySessionId.set(s.id, {
        session: s,
        meta:
          meta ||
          ({
            sessionId: s.id,
            title: s.last_message || `Investigation ${s.id}`,
            templateId: "custom",
            severity: "P3",
            status: "running",
            trigger: "manual",
            authority: "read_only",
            createdAt: s.created_at * 1000,
            updatedAt: s.created_at * 1000,
          } satisfies InvestigationMeta),
      });
    }
    // Surface investigations that exist in local store but not in live API,
    // so an operator never loses sight of the work record.
    for (const sessionId of Object.keys(investigations)) {
      if (bySessionId.has(sessionId)) continue;
      const meta = investigations[sessionId];
      bySessionId.set(sessionId, {
        session: {
          id: sessionId,
          status: meta.status,
          services: [],
          created_at: meta.createdAt / 1000,
          message_count: 0,
          last_message: meta.title,
        },
        meta,
      });
    }
    return Array.from(bySessionId.values());
  }, [sessions, investigations]);

  const stats = useMemo(() => {
    const total = enriched.length;
    const running = enriched.filter((e) => e.meta.status === "running").length;
    const needsReview = enriched.filter(
      (e) => e.meta.status === "needs_review",
    ).length;
    const resolvedToday = enriched.filter((e) => {
      if (e.meta.status !== "resolved" || !e.meta.resolvedAt) return false;
      return Date.now() - e.meta.resolvedAt < 24 * 60 * 60 * 1000;
    }).length;
    const p1 = enriched.filter(
      (e) => e.meta.severity === "P1" && e.meta.status !== "resolved",
    ).length;
    return { total, running, needsReview, resolvedToday, p1 };
  }, [enriched]);

  const filtered = useMemo(() => {
    return enriched.filter((row) => {
      if (
        filter === "active" &&
        !["running", "queued", "needs_review"].includes(row.meta.status)
      )
        return false;
      if (filter === "needs_review" && row.meta.status !== "needs_review")
        return false;
      if (filter === "resolved" && row.meta.status !== "resolved")
        return false;
      if (severityFilter && row.meta.severity !== severityFilter) return false;
      if (search) {
        const q = search.toLowerCase();
        if (
          !row.meta.title.toLowerCase().includes(q) &&
          !row.session.id.toLowerCase().includes(q) &&
          !(row.meta.triggerRef || "").toLowerCase().includes(q)
        )
          return false;
      }
      return true;
    });
  }, [enriched, filter, severityFilter, search]);

  const sorted = useMemo(() => {
    return filtered.slice().sort((a, b) => {
      const aRank = STATUS_ORDER.indexOf(a.meta.status);
      const bRank = STATUS_ORDER.indexOf(b.meta.status);
      if (aRank !== bRank) return aRank - bRank;
      return b.meta.updatedAt - a.meta.updatedAt;
    });
  }, [filtered]);

  return (
    <div className="flex h-full w-full flex-col overflow-hidden">
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-surface-1/60 px-6 backdrop-blur-md">
        <div>
          <h1 className="text-[14px] font-semibold tracking-tight text-text-primary">
            Inbox
          </h1>
          <p className="text-[11px] text-text-muted">
            Investigations dispatched to the Arcadia agent fleet
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge tone="success" size="sm" dot>
            {stats.running} agent{stats.running === 1 ? "" : "s"} running
          </Badge>
          <button
            onClick={() => navigate("/dispatch")}
            className="inline-flex h-9 items-center gap-2 rounded-lg bg-accent px-3 text-[13px] font-medium text-white shadow-sm transition-colors hover:bg-accent-hover"
          >
            <Send size={14} />
            Dispatch agent
          </button>
        </div>
      </header>

      <div className="grid shrink-0 grid-cols-5 gap-3 border-b border-border px-6 py-4">
        <StatCard
          label="Open"
          value={stats.total - stats.resolvedToday}
          icon={<ClipboardList size={15} />}
          tone="accent"
          hint="Active queue"
        />
        <StatCard
          label="P1 unresolved"
          value={stats.p1}
          icon={<AlertCircle size={15} />}
          tone={stats.p1 > 0 ? "danger" : "success"}
          hint={stats.p1 > 0 ? "Page on-call" : "Healthy"}
        />
        <StatCard
          label="Running"
          value={stats.running}
          icon={<Loader2 size={15} />}
          tone="info"
          hint="Agents in flight"
        />
        <StatCard
          label="Needs review"
          value={stats.needsReview}
          icon={<Hand size={15} />}
          tone="warning"
          hint="Awaiting human"
        />
        <StatCard
          label="Resolved 24h"
          value={stats.resolvedToday}
          icon={<CheckCircle2 size={15} />}
          tone="success"
          hint="Closed today"
        />
      </div>

      <div className="flex shrink-0 flex-wrap items-center gap-3 border-b border-border bg-surface-1/40 px-6 py-3">
        <SegmentedControl
          value={filter}
          onChange={setFilter}
          options={[
            { id: "all" as const, label: "All", count: enriched.length },
            {
              id: "active" as const,
              label: "Active",
              count: enriched.filter((e) =>
                ["running", "queued", "needs_review"].includes(e.meta.status),
              ).length,
            },
            {
              id: "needs_review" as const,
              label: "Needs review",
              count: stats.needsReview,
            },
            {
              id: "resolved" as const,
              label: "Resolved",
              count: enriched.filter((e) => e.meta.status === "resolved").length,
            },
          ]}
        />

        <div className="inline-flex items-center gap-1 rounded-lg border border-border bg-surface-2 p-0.5">
          {SEVERITY_ORDER.map((sev) => {
            const active = severityFilter === sev;
            return (
              <button
                key={sev}
                onClick={() => setSeverityFilter(active ? null : sev)}
                className={cn(
                  "rounded-md px-2 py-1 font-mono text-[11px] font-semibold transition-colors",
                  active
                    ? "bg-surface-4 text-text-primary"
                    : "text-text-muted hover:text-text-secondary",
                )}
              >
                {sev}
              </button>
            );
          })}
        </div>

        <div className="relative ml-auto">
          <Search
            size={12}
            className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted"
          />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by title, ID, or ref…"
            className="h-8 w-72 rounded-md border border-border bg-surface-2 pl-7 pr-2.5 text-[12px] text-text-primary placeholder:text-text-muted focus:border-accent"
          />
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-16 text-text-muted">
            <Loader2 size={14} className="mr-2 animate-spin" />
            <span className="text-[13px]">Loading inbox…</span>
          </div>
        ) : enriched.length === 0 ? (
          <EmptyState
            icon={<ClipboardList size={22} />}
            title="No investigations yet"
            description="Dispatch an agent to begin. Pick a workspace template, give the agent a brief, and it will run asynchronously — you'll see it appear here."
            size="lg"
            action={
              <button
                onClick={() => navigate("/dispatch")}
                className="inline-flex h-9 items-center gap-2 rounded-lg bg-accent px-3 text-[13px] font-medium text-white shadow-sm transition-colors hover:bg-accent-hover"
              >
                <Send size={14} />
                Dispatch first investigation
              </button>
            }
          />
        ) : sorted.length === 0 ? (
          <EmptyState
            icon={<Search size={22} />}
            title="No matches"
            description="No investigations match the current filters. Clear them to see the full queue."
            size="md"
          />
        ) : (
          <ul className="divide-y divide-border">
            {sorted.map((row) => (
              <InvestigationRow
                key={row.session.id}
                row={row}
                onOpen={() => navigate(`/investigations/${row.session.id}`)}
              />
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

interface EnrichedRow {
  session: SessionRow;
  meta: InvestigationMeta;
}

function InvestigationRow({
  row,
  onOpen,
}: {
  row: EnrichedRow;
  onOpen: () => void;
}) {
  const template = findTemplate(row.meta.templateId);
  const lastUpdated = row.meta.updatedAt;
  const ageMs = Date.now() - lastUpdated;
  const isStale =
    ageMs > 24 * 60 * 60 * 1000 && row.meta.status === "running";

  return (
    <li
      onClick={onOpen}
      className="group grid cursor-pointer grid-cols-[auto_1fr_auto] items-center gap-4 px-6 py-3 transition-colors hover:bg-surface-1/60"
    >
      <span
        className={cn(
          "h-2 w-2 shrink-0 rounded-full",
          row.meta.status === "running" && "bg-info animate-pulse",
          row.meta.status === "needs_review" && "bg-warning",
          row.meta.status === "queued" && "bg-text-muted",
          row.meta.status === "resolved" && "bg-success",
          row.meta.status === "escalated" && "bg-danger",
          row.meta.status === "cancelled" && "bg-text-faint",
        )}
      />

      <div className="min-w-0">
        <div className="mb-1 flex items-center gap-2">
          <SeverityBadge severity={row.meta.severity} size="xs" />
          <span className="truncate text-[13.5px] font-semibold text-text-primary group-hover:text-accent">
            {row.meta.title}
          </span>
          <span className="shrink-0 font-mono text-[10.5px] text-text-faint">
            {row.session.id}
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
          <StatusBadge status={row.meta.status} size="xs" />
          <TriggerBadge
            trigger={row.meta.trigger}
            triggerRef={row.meta.triggerRef}
            size="xs"
          />
          <span className="rounded border border-border bg-surface-2 px-1.5 py-0.5 font-mono text-[10px] text-text-muted">
            {template.title}
          </span>
          <span className="text-text-muted">·</span>
          <span className="inline-flex items-center gap-1 text-text-muted">
            <Activity size={10} />
            {row.session.message_count} msg
          </span>
          {row.session.services.length > 0 && (
            <>
              <span className="text-text-muted">·</span>
              <span className="text-text-muted">
                {row.session.services.slice(0, 3).join(" · ")}
                {row.session.services.length > 3 && " …"}
              </span>
            </>
          )}
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-3 text-[11px] text-text-muted">
        <div className="text-right">
          <div className="font-mono">
            {timeAgo(lastUpdated / 1000)}
          </div>
          {isStale && (
            <div className="mt-0.5 inline-flex items-center gap-1 font-mono text-[10px] text-warning">
              <Clock size={10} />
              stale
            </div>
          )}
        </div>
        <ChevronRight
          size={14}
          className="text-text-faint transition-transform group-hover:translate-x-0.5 group-hover:text-text-secondary"
        />
      </div>
    </li>
  );
}
