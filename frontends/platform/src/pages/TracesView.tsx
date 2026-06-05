import { useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ChevronRight,
  Database,
  Globe,
  Layers,
  Terminal,
  Wrench,
  X,
} from "lucide-react";
import type {
  StreamEvent,
  CommandEvent,
  OpEvent,
  McpToolCallEvent,
  MockRequestEvent,
} from "@/types";
import { formatTime, formatBytes, cn } from "@/lib/utils";
import {
  Badge,
  EmptyState,
  SegmentedControl,
  StatCard,
} from "@/components/ui";
import { stepColor } from "@/lib/stepColor";

type EventFilter = "all" | "command" | "op" | "mcp_tool_call" | "mock_request";

const MOUNT_COLORS: Record<string, string> = {
  "/tickets": "text-mount-tickets",
  "/slack": "text-mount-slack",
  "/github": "text-mount-github",
  "/pagerduty": "text-mount-pagerduty",
  "/finance": "text-mount-finance",
  "/datadog": "text-mount-datadog",
  "/compliance": "text-mount-compliance",
  "/customers": "text-mount-customers",
};

const TYPE_META: Record<
  string,
  { label: string; icon: React.ReactNode; accent: string; border: string }
> = {
  command: {
    label: "command",
    icon: <Terminal size={11} />,
    accent: "text-accent bg-accent-soft",
    border: "border-l-accent",
  },
  op: {
    label: "vfs op",
    icon: <Database size={11} />,
    accent: "text-info bg-info-soft",
    border: "border-l-info",
  },
  mcp_tool_call: {
    label: "mcp",
    icon: <Wrench size={11} />,
    accent: "text-warning bg-warning-soft",
    border: "border-l-warning",
  },
  mock_request: {
    label: "http",
    icon: <Globe size={11} />,
    accent: "text-text-secondary bg-surface-3",
    border: "border-l-text-muted",
  },
};

interface Props {
  events: StreamEvent[];
}

function eventSessionId(e: StreamEvent): string | null {
  const s = (e as { session?: string }).session;
  return s || null;
}

export default function TracesView({ events }: Props) {
  const [filter, setFilter] = useState<EventFilter>("all");
  const [expandedSet, setExpandedSet] = useState<Set<number>>(new Set());
  const [sessionFilter, setSessionFilter] = useState<string | null>(null);

  const sessionStats = useMemo(() => {
    const m = new Map<string, { id: string; count: number; lastTs: number; errors: number }>();
    for (const e of events) {
      const sid = eventSessionId(e);
      if (!sid) continue;
      const cur = m.get(sid) || { id: sid, count: 0, lastTs: 0, errors: 0 };
      cur.count++;
      cur.lastTs = Math.max(cur.lastTs, e.timestamp);
      if (e.type === "command" && (e as CommandEvent).exit_code !== 0) cur.errors++;
      m.set(sid, cur);
    }
    return Array.from(m.values()).sort((a, b) => b.lastTs - a.lastTs);
  }, [events]);

  const filtered = useMemo(() => {
    return events.filter((e) => {
      if (filter !== "all" && e.type !== filter) return false;
      if (sessionFilter && eventSessionId(e) !== sessionFilter) return false;
      return true;
    });
  }, [events, filter, sessionFilter]);

  const stats = useMemo(() => {
    const commands = events.filter((e) => e.type === "command").length;
    const ops = events.filter((e) => e.type === "op").length;
    const mcp = events.filter((e) => e.type === "mcp_tool_call").length;
    const errors = events.filter(
      (e) => e.type === "command" && (e as CommandEvent).exit_code !== 0,
    ).length;
    return { commands, ops, mcp, errors };
  }, [events]);

  const toggle = (idx: number) => {
    setExpandedSet((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border bg-surface-1/60 px-6 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <h1 className="text-[14px] font-semibold tracking-tight text-text-primary">
            Trace Timeline
          </h1>
          <Badge
            tone={events.length > 0 ? "info" : "outline"}
            size="sm"
            dot={events.length > 0}
          >
            {events.length > 0 ? "LIVE" : "Idle"}
          </Badge>
        </div>
        <p className="ml-1 text-[12px] text-text-muted">
          Real-time observability across commands, filesystem, and MCP traffic
        </p>
      </header>

      <div className="grid shrink-0 grid-cols-4 gap-3 px-6 py-4">
        <StatCard
          label="Commands"
          value={stats.commands}
          icon={<Terminal size={15} />}
          tone="accent"
          hint="Shell executions"
        />
        <StatCard
          label="VFS Ops"
          value={stats.ops}
          icon={<Database size={15} />}
          tone="info"
          hint="Filesystem reads / writes"
        />
        <StatCard
          label="MCP Calls"
          value={stats.mcp}
          icon={<Wrench size={15} />}
          tone="warning"
          hint="Tool invocations"
        />
        <StatCard
          label="Errors"
          value={stats.errors}
          icon={<AlertTriangle size={15} />}
          tone={stats.errors > 0 ? "danger" : "success"}
          hint={stats.errors > 0 ? "Investigate failures" : "Healthy"}
        />
      </div>

      <div className="flex shrink-0 items-center gap-3 border-b border-border bg-surface-1/40 px-6 py-3">
        <SegmentedControl
          value={filter}
          onChange={setFilter}
          options={[
            { id: "all", label: "All", count: events.length },
            { id: "command", label: "Commands", count: stats.commands },
            { id: "op", label: "VFS Ops", count: stats.ops },
            { id: "mcp_tool_call", label: "MCP", count: stats.mcp },
            {
              id: "mock_request",
              label: "Requests",
              count: events.filter((e) => e.type === "mock_request").length,
            },
          ]}
        />
        {sessionFilter && (
          <button
            onClick={() => setSessionFilter(null)}
            className="inline-flex items-center gap-1.5 rounded-full border border-accent/30 bg-accent-soft px-2.5 py-1 text-[11px] font-mono text-accent hover:bg-accent-soft/80"
            title="Clear session filter"
          >
            <Layers size={11} />
            {sessionFilter.slice(0, 18)}
            <X size={11} />
          </button>
        )}
        <span className="ml-auto font-mono text-[11px] text-text-muted">
          showing {filtered.length} of {events.length}
        </span>
      </div>

      <div className="flex min-h-0 flex-1 overflow-hidden">
        {sessionStats.length > 0 && (
          <aside className="flex w-[220px] shrink-0 flex-col border-r border-border bg-surface-1/30">
            <div className="border-b border-border px-3 py-2.5">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-text-muted">
                  Active sessions
                </span>
                <span className="font-mono text-[10px] text-text-faint">
                  {sessionStats.length}
                </span>
              </div>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto p-2">
              {sessionStats.map((s) => {
                const color = stepColor(s.id);
                const active = sessionFilter === s.id;
                return (
                  <button
                    key={s.id}
                    onClick={() =>
                      setSessionFilter(active ? null : s.id)
                    }
                    className={cn(
                      "group relative mb-1 flex w-full items-center gap-2 rounded-md border px-2.5 py-1.5 text-left transition-all",
                      active
                        ? "border-accent/30 bg-accent-soft"
                        : "border-transparent hover:border-border hover:bg-surface-2",
                    )}
                  >
                    <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full", color.bg)} />
                    <div className="min-w-0 flex-1 leading-tight">
                      <div className="truncate font-mono text-[10.5px] text-text-primary">
                        {s.id}
                      </div>
                      <div className="mt-0.5 flex items-center gap-1.5 text-[10px] text-text-muted">
                        <span>{s.count} ev</span>
                        {s.errors > 0 && (
                          <span className="text-danger">· {s.errors} err</span>
                        )}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </aside>
        )}

        <div className="flex-1 overflow-y-auto">
          {filtered.length === 0 ? (
            <EmptyState
              icon={<Activity size={22} />}
              title="No trace events yet"
              description={
                sessionFilter
                  ? "No events match this session filter."
                  : "Start an agent session in the Workspace to see commands, VFS operations, MCP tool calls, and HTTP traffic stream through here in real time."
              }
              size="lg"
            />
          ) : (
            <div className="flex flex-col divide-y divide-border">
              {filtered.map((event, idx) => (
                <EventRow
                  key={idx}
                  event={event}
                  expanded={expandedSet.has(idx)}
                  onToggle={() => toggle(idx)}
                  onPickSession={(sid) => setSessionFilter(sid)}
                  highlightedSession={sessionFilter}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function EventRow({
  event,
  expanded,
  onToggle,
  onPickSession,
  highlightedSession,
}: {
  event: StreamEvent;
  expanded: boolean;
  onToggle: () => void;
  onPickSession?: (sid: string) => void;
  highlightedSession?: string | null;
}) {
  const meta = TYPE_META[event.type] || TYPE_META.mock_request;
  const sid = eventSessionId(event);
  const sessionColor = sid ? stepColor(sid) : null;
  const isHighlighted = sid && highlightedSession && sid === highlightedSession;

  return (
    <div
      onClick={onToggle}
      className={cn(
        "group cursor-pointer border-l-2 px-6 py-2.5 font-mono text-[12px] transition-colors hover:bg-surface-1/60",
        meta.border,
        isHighlighted && "bg-surface-1/40",
      )}
    >
      <div className="flex items-start gap-3">
        <span className="w-[64px] shrink-0 text-text-faint">
          {formatTime(event.timestamp)}
        </span>
        <span
          className={cn(
            "inline-flex h-[18px] shrink-0 items-center gap-1 rounded px-1.5 text-[10px] font-semibold uppercase tracking-wide",
            meta.accent,
          )}
        >
          {meta.icon}
          {meta.label}
        </span>
        {sid && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onPickSession?.(sid);
            }}
            title={`Filter by session ${sid}`}
            className="inline-flex h-[18px] shrink-0 items-center gap-1 rounded px-1.5 text-[10px] text-text-muted hover:bg-surface-3 hover:text-text-primary"
          >
            {sessionColor && (
              <span className={cn("h-1.5 w-1.5 rounded-full", sessionColor.bg)} />
            )}
            {sid.slice(0, 8)}
          </button>
        )}
        <div className="min-w-0 flex-1">
          <EventSummary event={event} />
        </div>
        <EventMeta event={event} />
        <ChevronRight
          size={12}
          className={cn(
            "shrink-0 text-text-faint transition-transform",
            expanded && "rotate-90",
          )}
        />
      </div>
      {expanded && <EventDetail event={event} />}
    </div>
  );
}

function EventSummary({ event }: { event: StreamEvent }) {
  switch (event.type) {
    case "command": {
      const cmd = event as CommandEvent;
      return (
        <span className="block truncate text-text-primary">{cmd.command}</span>
      );
    }
    case "op": {
      const op = event as OpEvent;
      const mount = op.mount_prefix || "/" + (op.path.split("/")[1] || "");
      const mountColor = MOUNT_COLORS[mount] || "text-text-muted";
      return (
        <span className="flex items-center gap-2">
          <span className="text-accent">{op.op}</span>
          <span className="truncate text-text-secondary">{op.path}</span>
          <span
            className={cn(
              "shrink-0 rounded border border-border bg-surface-2 px-1.5 py-0.5 text-[10px]",
              mountColor,
            )}
          >
            {mount}
          </span>
        </span>
      );
    }
    case "mcp_tool_call": {
      const mcp = event as McpToolCallEvent;
      return (
        <span className="text-text-secondary">
          <span className="text-warning">{mcp.tool}</span>{" "}
          <span className="text-text-muted">
            {JSON.stringify(mcp.arguments).slice(0, 80)}
          </span>
        </span>
      );
    }
    case "mock_request": {
      const req = event as MockRequestEvent;
      return (
        <span className="flex items-center gap-2 text-text-secondary">
          <span className="rounded bg-surface-3 px-1.5 py-0.5 text-[10px] text-text-primary">
            {req.method}
          </span>
          <span className="truncate">{req.path}</span>
        </span>
      );
    }
    default:
      return <span className="text-text-muted">unknown event</span>;
  }
}

function EventMeta({ event }: { event: StreamEvent }) {
  switch (event.type) {
    case "command": {
      const cmd = event as CommandEvent;
      return (
        <Badge
          tone={cmd.exit_code === 0 ? "success" : "danger"}
          size="xs"
          mono
        >
          exit {cmd.exit_code}
        </Badge>
      );
    }
    case "op": {
      const op = event as OpEvent;
      return (
        <span className="font-mono text-[11px] text-text-muted">
          {formatBytes(op.bytes)}
        </span>
      );
    }
    case "mcp_tool_call": {
      const mcp = event as McpToolCallEvent;
      return (
        <span className="font-mono text-[11px] text-text-muted">
          {mcp.duration_ms}ms
        </span>
      );
    }
    case "mock_request": {
      const req = event as MockRequestEvent;
      return (
        <Badge
          tone={req.status_code < 400 ? "success" : "danger"}
          size="xs"
          mono
        >
          {req.status_code}
        </Badge>
      );
    }
    default:
      return null;
  }
}

function EventDetail({ event }: { event: StreamEvent }) {
  switch (event.type) {
    case "command": {
      const cmd = event as CommandEvent;
      if (!cmd.stdout) return null;
      return (
        <pre className="mt-3 max-h-48 overflow-auto whitespace-pre-wrap rounded-lg border border-border bg-surface-0 p-3 text-[11px] leading-relaxed text-text-secondary">
          {cmd.stdout}
        </pre>
      );
    }
    case "mcp_tool_call": {
      const mcp = event as McpToolCallEvent;
      return (
        <div className="mt-3 grid gap-2">
          <DetailBlock label="Arguments">
            <pre className="whitespace-pre-wrap text-[11px] text-text-secondary">
              {JSON.stringify(mcp.arguments, null, 2)}
            </pre>
          </DetailBlock>
          <DetailBlock label="Result">
            <pre className="max-h-48 overflow-auto whitespace-pre-wrap text-[11px] text-text-secondary">
              {mcp.error ? (
                <span className="text-danger">{mcp.error}</span>
              ) : (
                mcp.result
              )}
            </pre>
          </DetailBlock>
        </div>
      );
    }
    default:
      return (
        <pre className="mt-3 rounded-lg border border-border bg-surface-0 p-3 text-[11px] text-text-muted">
          {JSON.stringify(event, null, 2)}
        </pre>
      );
  }
}

function DetailBlock({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface-0 p-3">
      <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-text-muted">
        {label}
      </div>
      {children}
    </div>
  );
}
