import { useState, useEffect } from "react";
import { fetchIncidents, fetchDeployments } from "../api/client";
import type { PagerDutyIncident, Deployment } from "../types";

function severityClass(s: string) {
  const map: Record<string, string> = {
    critical: "critical",
    high: "high",
    warning: "warning",
    low: "low",
    info: "low",
  };
  return map[s?.toLowerCase()] || "";
}

function severityBadge(s: string) {
  const map: Record<string, string> = {
    critical: "danger",
    high: "orange",
    warning: "warning",
    low: "info",
    info: "info",
  };
  return map[s?.toLowerCase()] || "neutral";
}

function statusBadge(s: string) {
  const map: Record<string, string> = {
    triggered: "danger",
    acknowledged: "warning",
    resolved: "success",
    success: "success",
    failure: "danger",
    in_progress: "info",
    pending: "warning",
  };
  return map[s?.toLowerCase()] || "neutral";
}

function formatDate(d: string) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function EngineeringDashboard() {
  const [incidents, setIncidents] = useState<PagerDutyIncident[]>([]);
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchIncidents(), fetchDeployments()])
      .then(([inc, dep]) => {
        setIncidents(inc || []);
        setDeployments(dep || []);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading engineering data...</div>;

  const hasData = incidents.length > 0 || deployments.length > 0;
  if (!hasData) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">⚙️</div>
        <div className="empty-state-text">
          No engineering data found. Run <code>uv run mirage-eval seed --scenario acme_corp</code> to generate data.
        </div>
      </div>
    );
  }

  const activeIncidents = incidents.filter(
    (i) => i.status?.toLowerCase() !== "resolved"
  );
  const criticalCount = incidents.filter(
    (i) => i.severity?.toLowerCase() === "critical"
  ).length;
  const services = new Set(incidents.map((i) => i.service).filter(Boolean));

  return (
    <div>
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Active Incidents</div>
          <div className="stat-value danger">{activeIncidents.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Critical</div>
          <div className="stat-value" style={{ color: "var(--red)" }}>{criticalCount}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Deployments</div>
          <div className="stat-value">{deployments.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Services</div>
          <div className="stat-value">{services.size}</div>
        </div>
      </div>

      {incidents.length > 0 && (
        <div className="section">
          <div className="section-title">Incidents</div>
          <div className="incident-grid">
            {incidents.map((inc) => (
              <div key={inc.id} className={`incident-card ${severityClass(inc.severity)}`}>
                <div className="flex items-center gap-2 mb-3">
                  <span className={`badge ${severityBadge(inc.severity)}`}>{inc.severity}</span>
                  <span className={`badge ${statusBadge(inc.status)}`}>{inc.status}</span>
                </div>
                <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 14 }}>{inc.title}</div>
                <div className="resource-node-stats">
                  <div className="resource-node-stat">
                    <span>Service</span>
                    <span>{inc.service}</span>
                  </div>
                  <div className="resource-node-stat">
                    <span>Assignee</span>
                    <span>{inc.assignee || "Unassigned"}</span>
                  </div>
                  <div className="resource-node-stat">
                    <span>Created</span>
                    <span>{formatDate(inc.created_at)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {deployments.length > 0 && (
        <div className="section">
          <div className="card">
            <div className="card-header">
              <span className="card-title">Recent Deployments</span>
              <span className="badge neutral">{deployments.length} total</span>
            </div>
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Ref</th>
                  <th>Environment</th>
                  <th>Status</th>
                  <th>Creator</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {deployments.map((d) => (
                  <tr key={d.id}>
                    <td>{d.id}</td>
                    <td>{d.ref}</td>
                    <td><span className="badge purple">{d.environment}</span></td>
                    <td><span className={`badge ${statusBadge(d.status)}`}>{d.status}</span></td>
                    <td>{d.creator}</td>
                    <td>{formatDate(d.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
