import { useEffect, useMemo, useRef, useState } from "react";
import type { StreamEvent } from "../types";

function formatTime(ms: number): string {
  const d = new Date(ms);
  return d.toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function exitBadge(code: number) {
  const cls = code === 0 ? "success" : "danger";
  return <span className={`badge ${cls}`}>exit={code}</span>;
}

function MountBadge({ mount }: { mount: string }) {
  const colorMap: Record<string, string> = {
    "/pagerduty": "orange",
    "/slack": "purple",
    "/tickets": "info",
    "/github": "neutral",
    "/datadog": "cyan",
    "/finance": "warning",
    "/sheets": "purple",
    "/customers": "cyan",
    "/compliance": "info",
  };
  const cls = colorMap[mount] || "neutral";
  return <span className={`badge ${cls}`}>{mount}</span>;
}

interface CommandRow {
  timestamp: number;
  command: string;
  exit_code: number;
  stdout: string | null;
  mount: string;
}

interface Props {
  events: StreamEvent[];
  sessionId: string | null;
}

export default function LiveExecutionView({ events, sessionId }: Props) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const bottomRef = useRef<HTMLDivElement>(null);

  const rows = useMemo(() => {
    if (!sessionId) return [];
    return events
      .filter(
        (e) =>
          e.type === "command" &&
          ((e as Record<string, unknown>).session === sessionId ||
            e.session_id === sessionId),
      )
      .map((e) => {
        const cmd = e as Record<string, unknown>;
        const command = (cmd.command as string) || "";
        const parts = command.split(" ");
        const lastArg = parts[parts.length - 1] || "";
        const mount =
          lastArg.startsWith("/") && lastArg.includes("/")
            ? "/" + lastArg.split("/")[1]
            : "/";
        return {
          timestamp: e.timestamp,
          command,
          exit_code: (cmd.exit_code as number) ?? 0,
          stdout: (cmd.stdout as string) || null,
          mount,
        } as CommandRow;
      });
  }, [events, sessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [rows.length]);

  const toggleExpand = (idx: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  if (!sessionId) {
    return (
      <div className="empty-state" style={{ padding: "40px 20px" }}>
        <div className="empty-state-icon">$</div>
        <div className="empty-state-text">
          No active session. Start a task to see live execution.
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: "0 0 8px" }}>
      <div className="flex items-center gap-3" style={{ padding: "12px 16px" }}>
        <span className="card-title">Live Execution</span>
        {rows.length > 0 && <span className="badge info pulse">LIVE</span>}
        <span
          className="text-sm text-tertiary"
          style={{ marginLeft: "auto" }}
        >
          {rows.length} commands
        </span>
      </div>
      <div className="timeline">
        {rows.length === 0 && (
          <div
            style={{
              padding: "24px 16px",
              textAlign: "center",
              color: "var(--text-tertiary)",
              fontSize: 13,
            }}
          >
            <span className="pulse">Waiting for agent...</span>
          </div>
        )}
        {rows.map((row, idx) => {
          const isExpanded = expanded.has(idx);
          return (
            <div
              key={idx}
              className="timeline-entry"
              onClick={() => toggleExpand(idx)}
              style={{ cursor: "pointer" }}
            >
              <div className="timeline-time">{formatTime(row.timestamp)}</div>
              <div>
                <div className="timeline-command">{row.command}</div>
                {isExpanded && row.stdout && (
                  <div className="timeline-stdout">{row.stdout}</div>
                )}
                {row.mount !== "/" && (
                  <div className="timeline-ops">
                    <MountBadge mount={row.mount} />
                  </div>
                )}
              </div>
              <div className="timeline-meta">{exitBadge(row.exit_code)}</div>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
