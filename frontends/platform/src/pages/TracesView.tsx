import { useMemo, useState } from "react";
import type {
  StreamEvent,
  CommandEvent,
  OpEvent,
  McpToolCallEvent,
  MockRequestEvent,
} from "@/types";
import { formatTime, formatBytes } from "@/lib/utils";

type EventFilter = "all" | "command" | "op" | "mcp_tool_call" | "mock_request";

const FILTERS: { id: EventFilter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "command", label: "Commands" },
  { id: "op", label: "VFS Ops" },
  { id: "mcp_tool_call", label: "MCP" },
  { id: "mock_request", label: "Requests" },
];

const MOUNT_COLORS: Record<string, string> = {
  "/tickets": "bg-mount-tickets text-mount-tickets",
  "/slack": "bg-mount-slack/15 text-mount-slack",
  "/github": "bg-mount-github/15 text-mount-github",
  "/pagerduty": "bg-mount-pagerduty/15 text-mount-pagerduty",
  "/finance": "bg-mount-finance/15 text-mount-finance",
  "/datadog": "bg-mount-datadog/15 text-mount-datadog",
  "/compliance": "bg-mount-compliance/15 text-mount-compliance",
  "/customers": "bg-mount-customers/15 text-mount-customers",
};

interface Props {
  events: StreamEvent[];
}

export default function TracesView({ events }: Props) {
  const [filter, setFilter] = useState<EventFilter>("all");
  const [expandedSet, setExpandedSet] = useState<Set<number>>(new Set());

  const filtered = useMemo(() => {
    if (filter === "all") return events;
    return events.filter((e) => e.type === filter);
  }, [events, filter]);

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
      <div className="flex items-center gap-4 border-b border-border px-6 py-4">
        <h1 className="text-base font-semibold text-text-primary">
          Trace Timeline
        </h1>
        {events.length > 0 && (
          <span className="animate-pulse-fade rounded-full bg-info-muted px-2 py-0.5 font-mono text-[10px] font-medium text-info">
            LIVE
          </span>
        )}
      </div>

      <div className="grid grid-cols-4 gap-3 border-b border-border px-6 py-4">
        <StatCard label="Commands" value={stats.commands} />
        <StatCard label="VFS Ops" value={stats.ops} />
        <StatCard label="MCP Calls" value={stats.mcp} />
        <StatCard
          label="Errors"
          value={stats.errors}
          variant={stats.errors > 0 ? "danger" : "success"}
        />
      </div>

      <div className="flex gap-2 border-b border-border px-6 py-3">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              filter === f.id
                ? "bg-accent-muted text-accent"
                : "text-text-muted hover:bg-surface-3 hover:text-text-primary"
            }`}
          >
            {f.label}
          </button>
        ))}
        <span className="ml-auto font-mono text-xs text-text-muted">
          {filtered.length} events
        </span>
      </div>

      <div className="flex-1 overflow-y-auto">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-2 py-20">
            <span className="text-3xl opacity-30">$</span>
            <span className="text-sm text-text-muted">
              No events yet. Start an agent session to see trace activity.
            </span>
          </div>
        ) : (
          <div className="flex flex-col">
            {filtered.map((event, idx) => (
              <EventRow
                key={idx}
                event={event}
                expanded={expandedSet.has(idx)}
                onToggle={() => toggle(idx)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  variant,
}: {
  label: string;
  value: number;
  variant?: "success" | "danger";
}) {
  const valueColor =
    variant === "danger"
      ? "text-danger"
      : variant === "success"
        ? "text-success"
        : "text-text-primary";
  return (
    <div className="rounded-lg border border-border bg-surface-1 px-4 py-3">
      <div className="text-[10px] font-medium uppercase tracking-wider text-text-muted">
        {label}
      </div>
      <div className={`mt-1 text-xl font-bold tabular-nums ${valueColor}`}>
        {value}
      </div>
    </div>
  );
}

function EventRow({
  event,
  expanded,
  onToggle,
}: {
  event: StreamEvent;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <div
      onClick={onToggle}
      className="cursor-pointer border-b border-border px-6 py-2.5 font-mono text-xs transition-colors hover:bg-surface-2"
    >
      <div className="flex items-start gap-3">
        <span className="w-[70px] shrink-0 text-text-muted">
          {formatTime(event.timestamp)}
        </span>
        <span className="shrink-0">
          <TypeBadge type={event.type} />
        </span>
        <div className="min-w-0 flex-1">
          <EventSummary event={event} />
        </div>
        <EventMeta event={event} />
      </div>
      {expanded && <EventDetail event={event} />}
    </div>
  );
}

function TypeBadge({ type }: { type: string }) {
  const styles: Record<string, string> = {
    command: "bg-accent-muted text-accent",
    op: "bg-info-muted text-info",
    mcp_tool_call: "bg-warning-muted text-warning",
    mock_request: "bg-surface-3 text-text-secondary",
  };
  return (
    <span
      className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-medium ${styles[type] || "bg-surface-3 text-text-muted"}`}
    >
      {type === "mcp_tool_call" ? "mcp" : type === "mock_request" ? "http" : type}
    </span>
  );
}

function EventSummary({ event }: { event: StreamEvent }) {
  switch (event.type) {
    case "command": {
      const cmd = event as CommandEvent;
      return <span className="text-text-primary">{cmd.command}</span>;
    }
    case "op": {
      const op = event as OpEvent;
      const mount = op.mount_prefix || "/" + (op.path.split("/")[1] || "");
      const mountColor = MOUNT_COLORS[mount] || "bg-surface-3 text-text-secondary";
      return (
        <span className="flex items-center gap-2">
          <span className="text-text-secondary">
            {op.op} {op.path}
          </span>
          <span className={`rounded px-1 py-0.5 text-[10px] ${mountColor}`}>
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
          {JSON.stringify(mcp.arguments).slice(0, 80)}
        </span>
      );
    }
    case "mock_request": {
      const req = event as MockRequestEvent;
      return (
        <span className="text-text-secondary">
          <span className="text-text-primary">{req.method}</span> {req.path}
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
      const cls = cmd.exit_code === 0 ? "bg-success-muted text-success" : "bg-danger-muted text-danger";
      return (
        <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${cls}`}>
          exit={cmd.exit_code}
        </span>
      );
    }
    case "op": {
      const op = event as OpEvent;
      return (
        <span className="text-text-muted">{formatBytes(op.bytes)}</span>
      );
    }
    case "mcp_tool_call": {
      const mcp = event as McpToolCallEvent;
      return (
        <span className="text-text-muted">{mcp.duration_ms}ms</span>
      );
    }
    case "mock_request": {
      const req = event as MockRequestEvent;
      const cls = req.status_code < 400 ? "text-success" : "text-danger";
      return <span className={cls}>{req.status_code}</span>;
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
        <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap rounded bg-surface-0 p-3 text-[11px] text-text-secondary">
          {cmd.stdout}
        </pre>
      );
    }
    case "mcp_tool_call": {
      const mcp = event as McpToolCallEvent;
      return (
        <div className="mt-2 space-y-2">
          <div className="rounded bg-surface-0 p-3">
            <div className="mb-1 text-[10px] font-medium uppercase text-text-muted">
              Arguments
            </div>
            <pre className="whitespace-pre-wrap text-[11px] text-text-secondary">
              {JSON.stringify(mcp.arguments, null, 2)}
            </pre>
          </div>
          <div className="rounded bg-surface-0 p-3">
            <div className="mb-1 text-[10px] font-medium uppercase text-text-muted">
              Result
            </div>
            <pre className="max-h-40 overflow-auto whitespace-pre-wrap text-[11px] text-text-secondary">
              {mcp.error ? (
                <span className="text-danger">{mcp.error}</span>
              ) : (
                mcp.result
              )}
            </pre>
          </div>
        </div>
      );
    }
    default:
      return (
        <pre className="mt-2 rounded bg-surface-0 p-3 text-[11px] text-text-muted">
          {JSON.stringify(event, null, 2)}
        </pre>
      );
  }
}
