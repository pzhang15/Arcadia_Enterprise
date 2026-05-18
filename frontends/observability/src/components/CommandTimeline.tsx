import { useEffect, useMemo, useRef, useState } from "react";
import type { CommandEvent, OpEvent, StreamEvent } from "../types";

function formatTime(ms: number): string {
  const d = new Date(ms);
  return d.toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatBytes(b: number): string {
  if (b < 1024) return `${b}B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)}KB`;
  return `${(b / (1024 * 1024)).toFixed(1)}MB`;
}

function exitBadge(code: number) {
  const cls = code === 0 ? "success" : "danger";
  return <span className={`badge ${cls}`}>exit={code}</span>;
}

interface TimelineRow {
  command: CommandEvent;
  ops: OpEvent[];
}

function buildRows(events: StreamEvent[]): TimelineRow[] {
  const commands: CommandEvent[] = [];
  const opsByTimestamp: OpEvent[] = [];

  for (const e of events) {
    if (e.type === "command") commands.push(e);
    if (e.type === "op") opsByTimestamp.push(e);
  }

  return commands.map((cmd) => {
    const windowStart = cmd.timestamp - 50;
    const windowEnd = cmd.timestamp + 5000;
    const ops = opsByTimestamp.filter(
      (o) => o.timestamp >= windowStart && o.timestamp <= windowEnd,
    );
    return { command: cmd, ops };
  });
}

function MountBadge({ mount }: { mount: string }) {
  const colorMap: Record<string, string> = {
    "/pagerduty": "orange",
    "/slack": "purple",
    "/tickets": "info",
    "/github": "neutral",
    "/datadog": "cyan",
    "/dev": "warning",
  };
  const cls = colorMap[mount] || "neutral";
  return <span className={`badge ${cls}`}>{mount}</span>;
}

interface Props {
  events: StreamEvent[];
  onClear: () => void;
}

export default function CommandTimeline({ events, onClear }: Props) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [autoScroll, setAutoScroll] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  const rows = useMemo(() => buildRows(events), [events]);

  useEffect(() => {
    if (autoScroll && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [rows.length, autoScroll]);

  const toggleExpand = (idx: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const totalCommands = rows.length;
  const totalOps = events.filter((e) => e.type === "op").length;
  const failedCommands = rows.filter((r) => r.command.exit_code !== 0).length;

  return (
    <div>
      <div className="flex items-center gap-4 mb-5">
        <h1 style={{ fontSize: 18, fontWeight: 700 }}>Command Timeline</h1>
        <span className="badge info pulse">LIVE</span>
        <div style={{ marginLeft: "auto" }} className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-secondary" style={{ cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
            />
            Auto-scroll
          </label>
          <button className="filter-btn" onClick={onClear}>
            Clear
          </button>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Commands</div>
          <div className="stat-value">{totalCommands}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">I/O Ops</div>
          <div className="stat-value">{totalOps}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Failures</div>
          <div className={`stat-value ${failedCommands > 0 ? "danger" : "success"}`}>
            {failedCommands}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">Execution History</span>
          <span className="text-sm text-tertiary">
            {totalCommands} commands
          </span>
        </div>
        <div className="timeline" style={{ padding: "8px 0" }}>
          {rows.length === 0 && (
            <div className="empty-state">
              <div className="empty-state-icon">$</div>
              <div className="empty-state-text">
                Waiting for commands... Start an agent session to see activity
                here.
              </div>
            </div>
          )}
          {rows.map((row, idx) => {
            const isExpanded = expanded.has(idx);
            const cmd = row.command;
            const mounts = [
              ...new Set(
                row.ops.map((o) => o.mount_prefix || o.path.split("/").slice(0, 2).join("/")),
              ),
            ].filter(Boolean);

            return (
              <div
                key={idx}
                className="timeline-entry"
                onClick={() => toggleExpand(idx)}
                style={{ cursor: "pointer" }}
              >
                <div className="timeline-time">{formatTime(cmd.timestamp)}</div>
                <div>
                  <div className="timeline-command">{cmd.command}</div>
                  {isExpanded && cmd.stdout && (
                    <div className="timeline-stdout">{cmd.stdout}</div>
                  )}
                  {mounts.length > 0 && (
                    <div className="timeline-ops">
                      {mounts.map((m) => (
                        <MountBadge key={m} mount={m} />
                      ))}
                      {row.ops.length > 0 && (
                        <span className="badge neutral">
                          {formatBytes(
                            row.ops.reduce((s, o) => s + (o.bytes || 0), 0),
                          )}
                        </span>
                      )}
                    </div>
                  )}
                </div>
                <div className="timeline-meta">
                  {exitBadge(cmd.exit_code)}
                </div>
              </div>
            );
          })}
          <div ref={bottomRef} />
        </div>
      </div>
    </div>
  );
}
