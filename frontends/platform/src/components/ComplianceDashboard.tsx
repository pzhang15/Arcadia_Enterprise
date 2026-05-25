import { useState, useEffect } from "react";
import { fetchContracts, fetchAudits, fetchPolicies } from "../api/client";
import type { Contract, Audit, Policy } from "../types";

function statusBadge(s: string) {
  const map: Record<string, string> = {
    active: "success",
    approved: "success",
    completed: "success",
    passed: "success",
    in_review: "info",
    in_progress: "info",
    pending: "warning",
    draft: "warning",
    expired: "neutral",
    overdue: "danger",
    failed: "danger",
    terminated: "danger",
  };
  return map[s?.toLowerCase()] || "neutral";
}

function formatCurrency(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
}

function formatDate(d: string) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default function ComplianceDashboard() {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [audits, setAudits] = useState<Audit[]>([]);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchContracts(), fetchAudits(), fetchPolicies()])
      .then(([c, a, p]) => {
        setContracts(c || []);
        setAudits(a || []);
        setPolicies(p || []);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading compliance data...</div>;

  const hasData = contracts.length > 0 || audits.length > 0 || policies.length > 0;
  if (!hasData) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">📋</div>
        <div className="empty-state-text">
          No compliance data found. Run <code>uv run mirage-eval seed --scenario northhill_corp</code> to generate data.
        </div>
      </div>
    );
  }

  const inReview = contracts.filter((c) =>
    ["in_review", "pending", "draft"].includes(c.status?.toLowerCase())
  );

  const totalAuditItems = audits.reduce((s, a) => s + (a.checklist?.length || 0), 0);
  const completedAuditItems = audits.reduce(
    (s, a) => s + (a.checklist?.filter((c) =>
      ["completed", "passed"].includes(c.status?.toLowerCase())
    ).length || 0),
    0
  );
  const remainingAuditItems = totalAuditItems - completedAuditItems;

  const totalAcks = policies.reduce((s, p) => s + (p.acknowledgments?.length || 0), 0);
  const completedAcks = policies.reduce(
    (s, p) => s + (p.acknowledgments?.filter((a) => a.acked_at !== null).length || 0),
    0
  );
  const ackRate = totalAcks > 0 ? Math.round((completedAcks / totalAcks) * 100) : 0;

  return (
    <div>
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Contracts in Review</div>
          <div className="stat-value warning">{inReview.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Audit Items Remaining</div>
          <div className="stat-value" style={{ color: "var(--orange)" }}>{remainingAuditItems}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Policy Ack Rate</div>
          <div className="stat-value" style={{ color: ackRate >= 80 ? "var(--green)" : "var(--yellow)" }}>
            {ackRate}%
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total Policies</div>
          <div className="stat-value">{policies.length}</div>
        </div>
      </div>

      {contracts.length > 0 && (
        <div className="section">
          <div className="card">
            <div className="card-header">
              <span className="card-title">Contract Review Queue</span>
              <span className="badge neutral">{contracts.length} contracts</span>
            </div>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Contract ID</th>
                  <th>Counterparty</th>
                  <th>Type</th>
                  <th>Value</th>
                  <th>Status</th>
                  <th>Owner</th>
                  <th>End Date</th>
                </tr>
              </thead>
              <tbody>
                {contracts.map((c) => (
                  <tr key={c.contract_id}>
                    <td>{c.contract_id}</td>
                    <td style={{ fontFamily: "var(--font-sans)" }}>{c.counterparty}</td>
                    <td><span className="badge neutral">{c.type}</span></td>
                    <td>{formatCurrency(c.value)}</td>
                    <td><span className={`badge ${statusBadge(c.status)}`}>{c.status}</span></td>
                    <td>{c.owner}</td>
                    <td>{formatDate(c.end_date)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {audits.length > 0 && (
        <div className="section">
          <div className="section-title">Audit Progress</div>
          <div className="resource-map">
            {audits.map((a) => {
              const total = a.checklist?.length || 0;
              const done = a.checklist?.filter((c) =>
                ["completed", "passed"].includes(c.status?.toLowerCase())
              ).length || 0;
              const pct = total > 0 ? Math.round((done / total) * 100) : 0;
              return (
                <div key={a.audit_id} className="resource-node">
                  <div className="resource-node-header">
                    <span className="resource-node-name">{a.framework}</span>
                    <span className={`badge ${statusBadge(a.status)}`}>{a.status}</span>
                  </div>
                  <div className="resource-node-stats">
                    <div className="resource-node-stat">
                      <span>Due</span>
                      <span>{formatDate(a.due_date)}</span>
                    </div>
                    <div className="resource-node-stat">
                      <span>Progress</span>
                      <span>{done}/{total}</span>
                    </div>
                  </div>
                  <div className="progress-bar-bg" style={{ marginTop: 10 }}>
                    <div
                      className="progress-bar-fill"
                      style={{
                        width: `${pct}%`,
                        background: pct >= 80 ? "var(--green)" : pct >= 50 ? "var(--yellow)" : "var(--orange)",
                      }}
                    />
                  </div>
                  <div className="text-sm text-tertiary" style={{ marginTop: 4, textAlign: "right" }}>
                    {pct}% complete
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {policies.length > 0 && (
        <div className="section">
          <div className="section-title">Policy Acknowledgment Tracker</div>
          <div className="resource-map">
            {policies.map((p) => {
              const total = p.acknowledgments?.length || 0;
              const done = p.acknowledgments?.filter((a) => a.acked_at !== null).length || 0;
              const pct = total > 0 ? Math.round((done / total) * 100) : 0;
              return (
                <div key={p.policy_id} className="resource-node">
                  <div className="resource-node-header">
                    <span className="resource-node-name" style={{ fontSize: 13 }}>{p.title}</span>
                  </div>
                  <div className="resource-node-stats">
                    <div className="resource-node-stat">
                      <span>Version</span>
                      <span>{p.version}</span>
                    </div>
                    <div className="resource-node-stat">
                      <span>Effective</span>
                      <span>{formatDate(p.effective_date)}</span>
                    </div>
                    <div className="resource-node-stat">
                      <span>Acknowledged</span>
                      <span>{done}/{total}</span>
                    </div>
                  </div>
                  <div className="progress-bar-bg" style={{ marginTop: 10 }}>
                    <div
                      className="progress-bar-fill"
                      style={{
                        width: `${pct}%`,
                        background: pct === 100 ? "var(--green)" : pct >= 60 ? "var(--yellow)" : "var(--orange)",
                      }}
                    />
                  </div>
                  <div className="text-sm text-tertiary" style={{ marginTop: 4, textAlign: "right" }}>
                    {pct}% acknowledged
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
