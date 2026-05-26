import { useMemo, useState } from "react";
import type { MockRequestEvent, StreamEvent } from "../types";

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

const SERVICE_COLORS: Record<string, string> = {
  slack: "purple",
  github: "neutral",
  jira: "info",
  pagerduty: "orange",
  datadog: "cyan",
};

function statusBadge(code: number) {
  if (code < 300) return <span className="badge success">{code}</span>;
  if (code < 400) return <span className="badge warning">{code}</span>;
  return <span className="badge danger">{code}</span>;
}

function methodBadge(method: string) {
  const cls = method === "GET" ? "info" : method === "POST" ? "warning" : "neutral";
  return <span className="badge" style={{ minWidth: 40, justifyContent: "center" }} >{method}</span>;
}

interface Props {
  events: StreamEvent[];
}

export default function MockRequestLog({ events }: Props) {
  const [serviceFilter, setServiceFilter] = useState<string | null>(null);

  const requests = useMemo(
    () => events.filter((e): e is MockRequestEvent => e.type === "mock_request"),
    [events],
  );

  const services = useMemo(
    () => [...new Set(requests.map((r) => r.service))].sort(),
    [requests],
  );

  const filtered = serviceFilter
    ? requests.filter((r) => r.service === serviceFilter)
    : requests;

  const totalBytes = filtered.reduce((s, r) => s + r.response_bytes, 0);
  const avgLatency =
    filtered.length > 0
      ? filtered.reduce((s, r) => s + r.duration_ms, 0) / filtered.length
      : 0;

  return (
    <div>
      <div className="flex items-center gap-4 mb-5">
        <h1 style={{ fontSize: 18, fontWeight: 700 }}>Mock Backend Request Log</h1>
        <span className="badge info pulse">LIVE</span>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Requests</div>
          <div className="stat-value">{filtered.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total Response</div>
          <div className="stat-value">{formatBytes(totalBytes)}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Avg Latency</div>
          <div className="stat-value">{avgLatency.toFixed(1)}ms</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Services</div>
          <div className="stat-value">{services.length}</div>
        </div>
      </div>

      <div className="filter-bar">
        <button
          className={`filter-btn ${serviceFilter === null ? "active" : ""}`}
          onClick={() => setServiceFilter(null)}
        >
          All
        </button>
        {services.map((s) => (
          <button
            key={s}
            className={`filter-btn ${serviceFilter === s ? "active" : ""}`}
            onClick={() => setServiceFilter(s)}
          >
            {s}
          </button>
        ))}
      </div>

      <div className="card">
        <div style={{ overflowX: "auto" }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Service</th>
                <th>Method</th>
                <th>Path</th>
                <th>Status</th>
                <th style={{ textAlign: "right" }}>Size</th>
                <th style={{ textAlign: "right" }}>Latency</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={7}>
                    <div className="empty-state">
                      <div className="empty-state-icon">HTTP</div>
                      <div className="empty-state-text">
                        No requests yet. Run an agent to see mock backend traffic.
                      </div>
                    </div>
                  </td>
                </tr>
              )}
              {filtered.map((req, idx) => (
                <tr key={idx}>
                  <td>{formatTime(req.timestamp)}</td>
                  <td>
                    <span className={`badge ${SERVICE_COLORS[req.service] || "neutral"}`}>
                      {req.service}
                    </span>
                  </td>
                  <td>{methodBadge(req.method)}</td>
                  <td className="truncate" style={{ maxWidth: 400 }}>
                    {req.path}
                  </td>
                  <td>{statusBadge(req.status_code)}</td>
                  <td style={{ textAlign: "right" }}>
                    {formatBytes(req.response_bytes)}
                  </td>
                  <td style={{ textAlign: "right" }}>{req.duration_ms}ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
