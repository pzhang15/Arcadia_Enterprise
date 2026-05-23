import { useEffect, useState } from "react";
import { listTraces, getTrace, getTraceStats } from "../api/client";
import type { TraceSummary, TraceDetail, TraceSpan } from "../types";

const KIND_LABELS: Record<number, string> = { 0: "ROOT", 1: "INTERNAL", 2: "CLIENT" };
const LEVEL_LABELS: Record<number, string> = { 0: "AUDIT", 1: "TRACE", 2: "OPERATIONAL" };

function formatBytes(b: number): string {
  if (b === 0) return "0 B";
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDuration(ms: number): string {
  if (ms < 1) return "<1ms";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

function formatTime(ms: number): string {
  return new Date(ms).toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function SpanBar({
  span,
  traceStart,
  traceDuration,
  depth,
  selected,
  onClick,
}: {
  span: TraceSpan;
  traceStart: number;
  traceDuration: number;
  depth: number;
  selected: boolean;
  onClick: () => void;
}) {
  const spanDuration = span.end_time_ms - span.start_time_ms;
  const offset = traceDuration > 0 ? ((span.start_time_ms - traceStart) / traceDuration) * 100 : 0;
  const width = traceDuration > 0 ? Math.max((spanDuration / traceDuration) * 100, 0.5) : 100;
  const isError = span.status === 1;
  const isRoot = span.kind === 0;

  const barColor = isError
    ? "var(--red)"
    : isRoot
      ? "var(--accent)"
      : span.attributes?.cache_hit
        ? "var(--green)"
        : "var(--cyan)";

  return (
    <div
      className={`waterfall-row ${selected ? "selected" : ""}`}
      onClick={onClick}
    >
      <div className="waterfall-label" style={{ paddingLeft: depth * 20 + 8 }}>
        <span className={`waterfall-dot ${isError ? "error" : isRoot ? "root" : ""}`} />
        <span className="waterfall-name">{span.name}</span>
        {span.attributes?.path != null && (
          <span className="waterfall-path">{`${span.attributes.path}`}</span>
        )}
      </div>
      <div className="waterfall-bar-container">
        <div
          className="waterfall-bar"
          style={{
            left: `${offset}%`,
            width: `${width}%`,
            background: barColor,
          }}
        >
          <span className="waterfall-bar-label">{formatDuration(spanDuration)}</span>
        </div>
      </div>
    </div>
  );
}

function SpanDetail({ span }: { span: TraceSpan }) {
  const duration = span.end_time_ms - span.start_time_ms;
  const metrics = span.metrics;
  const attrs = span.attributes || {};

  return (
    <div className="span-detail">
      <div className="span-detail-header">
        <span className="span-detail-name">{span.name}</span>
        <span className={`badge ${span.status === 0 ? "success" : "danger"}`}>
          {span.status === 0 ? "OK" : "ERROR"}
        </span>
        <span className={`badge neutral`}>{KIND_LABELS[span.kind] || "UNKNOWN"}</span>
        <span className={`badge ${span.level === 0 ? "warning" : "info"}`}>
          {LEVEL_LABELS[span.level] || "UNKNOWN"}
        </span>
      </div>
      <div className="span-detail-grid">
        <div className="span-detail-section">
          <div className="span-detail-section-title">Timing</div>
          <div className="span-detail-row">
            <span>Duration</span><span>{formatDuration(duration)}</span>
          </div>
          <div className="span-detail-row">
            <span>Start</span><span>{formatTime(span.start_time_ms)}</span>
          </div>
          <div className="span-detail-row">
            <span>End</span><span>{formatTime(span.end_time_ms)}</span>
          </div>
        </div>
        {metrics && (
          <div className="span-detail-section">
            <div className="span-detail-section-title">Metrics</div>
            <div className="span-detail-row">
              <span>Bytes Read</span><span>{formatBytes(metrics.bytes_read)}</span>
            </div>
            <div className="span-detail-row">
              <span>Bytes Written</span><span>{formatBytes(metrics.bytes_written)}</span>
            </div>
            <div className="span-detail-row">
              <span>API Calls</span><span>{metrics.api_calls}</span>
            </div>
            <div className="span-detail-row">
              <span>Cache Hits</span><span>{metrics.cache_hits}</span>
            </div>
            <div className="span-detail-row">
              <span>Cache Misses</span><span>{metrics.cache_misses}</span>
            </div>
            {(metrics.cache_hits + metrics.cache_misses) > 0 && (
              <div className="span-detail-row">
                <span>Hit Rate</span>
                <span>{((metrics.cache_hits / (metrics.cache_hits + metrics.cache_misses)) * 100).toFixed(0)}%</span>
              </div>
            )}
          </div>
        )}
        {Object.keys(attrs).length > 0 && (
          <div className="span-detail-section">
            <div className="span-detail-section-title">Attributes</div>
            {Object.entries(attrs).map(([k, v]) => (
              <div className="span-detail-row" key={k}>
                <span>{k}</span>
                <span className="mono">{typeof v === "object" ? JSON.stringify(v) : String(v)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
      {span.events && span.events.length > 0 && (
        <div className="span-detail-section" style={{ marginTop: 12 }}>
          <div className="span-detail-section-title">Events ({span.events.length})</div>
          {span.events.map((e, i) => (
            <div className="span-detail-row" key={i}>
              <span>{e.name}</span>
              <span className="text-tertiary">{formatTime(e.timestamp_ms)}</span>
            </div>
          ))}
        </div>
      )}
      <div className="span-detail-ids">
        <span>trace: {span.trace_id.slice(0, 12)}...</span>
        <span>span: {span.span_id.slice(0, 12)}...</span>
        {span.parent_span_id && <span>parent: {span.parent_span_id.slice(0, 12)}...</span>}
      </div>
    </div>
  );
}

function orderSpans(spans: TraceSpan[]): { span: TraceSpan; depth: number }[] {
  const byParent: Record<string, TraceSpan[]> = {};
  for (const s of spans) {
    const pid = s.parent_span_id || "__root__";
    if (!byParent[pid]) byParent[pid] = [];
    byParent[pid].push(s);
  }
  for (const children of Object.values(byParent)) {
    children.sort((a, b) => a.start_time_ms - b.start_time_ms);
  }
  const result: { span: TraceSpan; depth: number }[] = [];
  const walk = (parentId: string, depth: number) => {
    const children = byParent[parentId] || [];
    for (const child of children) {
      result.push({ span: child, depth });
      walk(child.span_id, depth + 1);
    }
  };
  walk("__root__", 0);
  return result;
}

export default function TraceExplorer() {
  const [traces, setTraces] = useState<TraceSummary[]>([]);
  const [detail, setDetail] = useState<TraceDetail | null>(null);
  const [selectedSpan, setSelectedSpan] = useState<TraceSpan | null>(null);
  const [stats, setStats] = useState<{ total_traces: number; total_spans: number } | null>(null);
  const [loading, setLoading] = useState(false);

  const loadTraces = async () => {
    setLoading(true);
    try {
      const [t, s] = await Promise.all([listTraces(), getTraceStats()]);
      setTraces(t);
      setStats(s);
    } catch { /* relay may not have traces */ }
    setLoading(false);
  };

  useEffect(() => { loadTraces(); }, []);

  const openTrace = async (traceId: string) => {
    setLoading(true);
    setSelectedSpan(null);
    try {
      const d = await getTrace(traceId);
      setDetail(d);
      if (d.spans.length > 0) setSelectedSpan(d.spans[0]);
    } catch { /* ignore */ }
    setLoading(false);
  };

  if (detail) {
    const spans = detail.spans;
    const traceStart = Math.min(...spans.map((s) => s.start_time_ms));
    const traceEnd = Math.max(...spans.map((s) => s.end_time_ms));
    const traceDuration = traceEnd - traceStart;
    const ordered = orderSpans(spans);
    const root = spans.find((s) => s.parent_span_id === null) || spans[0];

    return (
      <div>
        <div className="flex items-center gap-3 mb-4">
          <button className="filter-btn" onClick={() => { setDetail(null); setSelectedSpan(null); }}>
            Back to Traces
          </button>
          <span className="mono text-secondary" style={{ fontSize: 13 }}>
            {String(root?.attributes?.command || detail.trace_id)}
          </span>
          <span className="text-tertiary text-sm" style={{ marginLeft: "auto" }}>
            {spans.length} spans &middot; {formatDuration(traceDuration)}
          </span>
        </div>

        <div className="trace-waterfall-container">
          <div className="card" style={{ flex: 1, minWidth: 0 }}>
            <div className="card-header">
              <span className="card-title">Waterfall</span>
              <span className="text-tertiary text-sm">{formatTime(traceStart)} &mdash; {formatTime(traceEnd)}</span>
            </div>
            <div className="waterfall-timeline">
              <div className="waterfall-ruler">
                <span>0ms</span>
                <span>{formatDuration(traceDuration / 4)}</span>
                <span>{formatDuration(traceDuration / 2)}</span>
                <span>{formatDuration((traceDuration * 3) / 4)}</span>
                <span>{formatDuration(traceDuration)}</span>
              </div>
              {ordered.map(({ span, depth }) => (
                <SpanBar
                  key={span.span_id}
                  span={span}
                  traceStart={traceStart}
                  traceDuration={traceDuration}
                  depth={depth}
                  selected={selectedSpan?.span_id === span.span_id}
                  onClick={() => setSelectedSpan(span)}
                />
              ))}
            </div>
          </div>
          {selectedSpan && (
            <div className="card trace-detail-panel">
              <div className="card-header">
                <span className="card-title">Span Detail</span>
                <button
                  className="filter-btn"
                  onClick={() => setSelectedSpan(null)}
                  style={{ padding: "2px 8px", fontSize: 11 }}
                >
                  Close
                </button>
              </div>
              <div className="card-body">
                <SpanDetail span={selectedSpan} />
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <h2 style={{ fontSize: 16, fontWeight: 600 }}>Trace Explorer</h2>
        <button className="filter-btn" onClick={loadTraces} disabled={loading}>
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Total Traces</div>
          <div className="stat-value">{stats?.total_traces ?? 0}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total Spans</div>
          <div className="stat-value">{stats?.total_spans ?? 0}</div>
        </div>
      </div>

      {traces.length === 0 && !loading && (
        <div className="empty-state">
          <div className="empty-state-icon">🔭</div>
          <div className="empty-state-text">
            No traces yet. Run the demo script to generate trace data:
            <br />
            <code>cd docker/trace-demo && docker compose up --build</code>
          </div>
        </div>
      )}

      {traces.length > 0 && (
        <div className="card">
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Command</th>
                <th>Status</th>
                <th>Duration</th>
                <th>Spans</th>
                <th>Bytes</th>
                <th>Cache</th>
              </tr>
            </thead>
            <tbody>
              {traces.map((t) => {
                const dur = t.end_time_ms - t.start_time_ms;
                const cmd = String(t.attributes?.command || "—");
                const m = t.metrics;
                const hitRate =
                  m && (m.cache_hits + m.cache_misses) > 0
                    ? ((m.cache_hits / (m.cache_hits + m.cache_misses)) * 100).toFixed(0) + "%"
                    : "—";
                return (
                  <tr
                    key={t.trace_id}
                    onClick={() => openTrace(t.trace_id)}
                    style={{ cursor: "pointer" }}
                  >
                    <td style={{ whiteSpace: "nowrap" }}>{formatTime(t.start_time_ms)}</td>
                    <td>
                      <span className="mono truncate" style={{ maxWidth: 400, display: "inline-block" }}>
                        {cmd}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${t.status === 0 ? "success" : "danger"}`}>
                        {t.status === 0 ? "OK" : "ERR"}
                      </span>
                    </td>
                    <td className="mono">{formatDuration(dur)}</td>
                    <td className="mono">{t.child_count + 1}</td>
                    <td className="mono">{m ? formatBytes(m.bytes_read + m.bytes_written) : "—"}</td>
                    <td className="mono">{hitRate}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
