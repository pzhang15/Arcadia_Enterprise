import { useMemo, useState } from "react";
import type { McpToolCallEvent, StreamEvent } from "../types";

function formatTime(ms: number): string {
  const d = new Date(ms);
  return d.toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function prettyJson(obj: unknown): string {
  try {
    return JSON.stringify(obj, null, 2);
  } catch {
    return String(obj);
  }
}

interface Props {
  events: StreamEvent[];
}

export default function McpTraffic({ events }: Props) {
  const [expandedSet, setExpandedSet] = useState<Set<number>>(new Set());

  const calls = useMemo(
    () =>
      events.filter(
        (e): e is McpToolCallEvent => e.type === "mcp_tool_call",
      ),
    [events],
  );

  const toggle = (idx: number) => {
    setExpandedSet((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const totalCalls = calls.length;
  const errors = calls.filter((c) => c.error).length;
  const avgDuration =
    totalCalls > 0
      ? calls.reduce((s, c) => s + c.duration_ms, 0) / totalCalls
      : 0;
  const totalBytes = calls.reduce((s, c) => s + c.result_bytes, 0);

  return (
    <div>
      <div className="flex items-center gap-4 mb-5">
        <h1 style={{ fontSize: 18, fontWeight: 700 }}>MCP Traffic Inspector</h1>
        <span className="badge info pulse">LIVE</span>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Tool Calls</div>
          <div className="stat-value">{totalCalls}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Errors</div>
          <div className={`stat-value ${errors > 0 ? "danger" : "success"}`}>
            {errors}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Avg Duration</div>
          <div className="stat-value">{avgDuration.toFixed(1)}ms</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total Bytes</div>
          <div className="stat-value">
            {totalBytes < 1024
              ? `${totalBytes}B`
              : `${(totalBytes / 1024).toFixed(1)}KB`}
          </div>
        </div>
      </div>

      {calls.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">&gt;_</div>
          <div className="empty-state-text">
            No MCP tool calls recorded yet. Start an agent session to see
            JSON-RPC traffic here.
          </div>
        </div>
      ) : (
        <div>
          {calls.map((call, idx) => {
            const isExpanded = expandedSet.has(idx);
            return (
              <div key={idx} className="mcp-pair">
                <div className="mcp-pair-header" onClick={() => toggle(idx)}>
                  <span style={{ color: "var(--text-tertiary)", fontSize: 11, minWidth: 70 }}>
                    {formatTime(call.timestamp)}
                  </span>
                  <span className="badge info">{call.tool}</span>
                  <span className="mono truncate" style={{ flex: 1, color: "var(--text-secondary)", fontSize: 12 }}>
                    {typeof call.arguments === "object"
                      ? JSON.stringify(call.arguments)
                      : ""}
                  </span>
                  <span className="badge neutral">{call.duration_ms}ms</span>
                  {call.error ? (
                    <span className="badge danger">ERROR</span>
                  ) : (
                    <span className="badge success">{call.result_bytes}B</span>
                  )}
                  <span style={{ color: "var(--text-tertiary)", fontSize: 12 }}>
                    {isExpanded ? "\u25B2" : "\u25BC"}
                  </span>
                </div>
                {isExpanded && (
                  <div className="mcp-pair-body">
                    <div className="mcp-panel">
                      <div className="mcp-panel-label">Request</div>
                      {prettyJson({
                        tool: call.tool,
                        arguments: call.arguments,
                      })}
                    </div>
                    <div className="mcp-panel">
                      <div className="mcp-panel-label">Response</div>
                      {call.error ? (
                        <span style={{ color: "var(--red)" }}>
                          {call.error}
                        </span>
                      ) : (
                        call.result
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
