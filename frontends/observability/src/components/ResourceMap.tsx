import { useMemo } from "react";
import type { MountStats, OpEvent, StreamEvent } from "../types";

function formatBytes(b: number): string {
  if (b < 1024) return `${b}B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)}KB`;
  return `${(b / (1024 * 1024)).toFixed(1)}MB`;
}

const MOUNT_COLORS: Record<string, string> = {
  "/pagerduty": "var(--orange)",
  "/slack": "var(--purple)",
  "/tickets": "var(--blue)",
  "/github": "var(--text-primary)",
  "/datadog": "var(--cyan)",
  "/dev": "var(--yellow)",
  "/.sessions": "var(--text-tertiary)",
};

function deriveMountStats(ops: OpEvent[]): MountStats[] {
  const byMount = new Map<string, OpEvent[]>();

  for (const op of ops) {
    const mount = op.mount_prefix || "/" + (op.path.split("/")[1] || "unknown");
    const existing = byMount.get(mount) || [];
    existing.push(op);
    byMount.set(mount, existing);
  }

  return [...byMount.entries()]
    .map(([mount, mountOps]) => ({
      mount,
      reads: mountOps.filter((o) => o.op === "read" || o.op === "read_bytes" || o.op === "readdir" || o.op === "stat").length,
      writes: mountOps.filter((o) => o.op === "write" || o.op === "write_bytes" || o.op === "append" || o.op === "mkdir").length,
      bytes: mountOps.reduce((s, o) => s + (o.bytes || 0), 0),
      ops: mountOps,
    }))
    .sort((a, b) => b.ops.length - a.ops.length);
}

interface Props {
  events: StreamEvent[];
}

export default function ResourceMap({ events }: Props) {
  const ops = useMemo(
    () => events.filter((e): e is OpEvent => e.type === "op"),
    [events],
  );

  const mounts = useMemo(() => deriveMountStats(ops), [ops]);

  const totalOps = ops.length;
  const totalBytes = ops.reduce((s, o) => s + (o.bytes || 0), 0);
  const cacheHits = ops.filter((o) => o.source === "ram").length;
  const cacheRate = totalOps > 0 ? (cacheHits / totalOps) * 100 : 0;

  return (
    <div>
      <div className="flex items-center gap-4 mb-5">
        <h1 style={{ fontSize: 18, fontWeight: 700 }}>Resource Access Map</h1>
        <span className="badge info pulse">LIVE</span>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Total Ops</div>
          <div className="stat-value">{totalOps}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Data Transferred</div>
          <div className="stat-value">{formatBytes(totalBytes)}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Mounts Touched</div>
          <div className="stat-value">{mounts.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Cache Hit Rate</div>
          <div className={`stat-value ${cacheRate > 20 ? "warning" : "success"}`}>
            {cacheRate.toFixed(1)}%
          </div>
        </div>
      </div>

      {mounts.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">&#x1F5C2;</div>
          <div className="empty-state-text">
            No resource access recorded yet. Commands that read/write mounted
            data will appear here.
          </div>
        </div>
      ) : (
        <>
          {/* Flow visualization */}
          <div className="card mb-5">
            <div className="card-header">
              <span className="card-title">Access Flow</span>
            </div>
            <div className="card-body">
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 12,
                  flexWrap: "wrap",
                  padding: "20px 0",
                }}
              >
                {mounts.map((m, idx) => (
                  <div key={m.mount} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <div
                      style={{
                        background: "var(--bg-tertiary)",
                        border: "1px solid var(--border)",
                        borderRadius: "var(--radius)",
                        padding: "12px 20px",
                        textAlign: "center",
                      }}
                    >
                      <div
                        className="mono"
                        style={{
                          fontWeight: 700,
                          fontSize: 14,
                          color: MOUNT_COLORS[m.mount] || "var(--text-primary)",
                          marginBottom: 4,
                        }}
                      >
                        {m.mount}
                      </div>
                      <div className="text-sm text-secondary">
                        {m.reads}r / {m.writes}w
                      </div>
                      <div className="text-sm text-tertiary">
                        {formatBytes(m.bytes)}
                      </div>
                    </div>
                    {idx < mounts.length - 1 && (
                      <div style={{ color: "var(--text-tertiary)", fontSize: 18 }}>
                        &rarr;
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Detail cards */}
          <div className="resource-map">
            {mounts.map((m) => (
              <div key={m.mount} className="resource-node">
                <div className="resource-node-header">
                  <span
                    className="resource-node-name"
                    style={{
                      color: MOUNT_COLORS[m.mount] || "var(--text-primary)",
                    }}
                  >
                    {m.mount}
                  </span>
                  <span className="badge neutral">{m.ops.length} ops</span>
                </div>
                <div className="resource-node-stats">
                  <div className="resource-node-stat">
                    <span>Reads</span>
                    <span>{m.reads}</span>
                  </div>
                  <div className="resource-node-stat">
                    <span>Writes</span>
                    <span>{m.writes}</span>
                  </div>
                  <div className="resource-node-stat">
                    <span>Bytes</span>
                    <span>{formatBytes(m.bytes)}</span>
                  </div>
                  <div className="resource-node-stat">
                    <span>Unique paths</span>
                    <span>
                      {new Set(m.ops.map((o) => o.path)).size}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
