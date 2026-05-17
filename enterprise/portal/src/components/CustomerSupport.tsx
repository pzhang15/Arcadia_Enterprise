import { useState, useEffect } from "react";
import { fetchTickets, fetchAccounts, fetchEscalations } from "../api/client";
import type { Ticket, CustomerAccount, Escalation } from "../types";

function statusBadge(s: string) {
  const map: Record<string, string> = {
    open: "warning",
    in_progress: "info",
    resolved: "success",
    closed: "neutral",
    pending: "warning",
    active: "info",
    escalated: "danger",
  };
  return map[s?.toLowerCase()] || "neutral";
}

function priorityBadge(p: string) {
  const map: Record<string, string> = {
    critical: "danger",
    high: "orange",
    medium: "warning",
    low: "info",
    normal: "neutral",
  };
  return map[p?.toLowerCase()] || "neutral";
}

function tierBadge(t: string) {
  const map: Record<string, string> = {
    enterprise: "purple",
    premium: "cyan",
    standard: "info",
    starter: "neutral",
  };
  return map[t?.toLowerCase()] || "neutral";
}

function healthColor(score: number) {
  if (score >= 80) return "var(--green)";
  if (score >= 50) return "var(--yellow)";
  return "var(--red)";
}

function formatCurrency(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
}

function formatDate(d: string) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default function CustomerSupport() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [accounts, setAccounts] = useState<CustomerAccount[]>([]);
  const [escalations, setEscalations] = useState<Escalation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetchTickets("support").catch(() => []),
      fetchAccounts(),
      fetchEscalations(),
    ])
      .then(([tix, acct, esc]) => {
        setTickets(tix || []);
        setAccounts(acct || []);
        setEscalations(esc || []);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading customer data...</div>;

  const hasData = tickets.length > 0 || accounts.length > 0 || escalations.length > 0;
  if (!hasData) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">🎯</div>
        <div className="empty-state-text">
          No customer data found. Run <code>uv run mirage-eval seed --scenario acme_corp</code> to generate data.
        </div>
      </div>
    );
  }

  const openTickets = tickets.filter((t) => t.status?.toLowerCase() !== "resolved" && t.status?.toLowerCase() !== "closed");
  const activeEscalations = escalations.filter((e) => e.status?.toLowerCase() !== "resolved");
  const atRisk = accounts.filter((a) => (a.health_score || 0) < 50);

  return (
    <div>
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Open Tickets</div>
          <div className="stat-value warning">{openTickets.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Escalations</div>
          <div className="stat-value danger">{activeEscalations.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">At-Risk Accounts</div>
          <div className="stat-value" style={{ color: "var(--orange)" }}>{atRisk.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total Accounts</div>
          <div className="stat-value">{accounts.length}</div>
        </div>
      </div>

      {tickets.length > 0 && (
        <div className="section">
          <div className="card">
            <div className="card-header">
              <span className="card-title">Support Queue</span>
              <span className="badge neutral">{tickets.length} tickets</span>
            </div>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Ticket ID</th>
                  <th>Subject</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th>Requester</th>
                  <th>Assignee</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {tickets.map((t) => (
                  <tr key={t.ticket_id}>
                    <td>{t.ticket_id}</td>
                    <td style={{ fontFamily: "var(--font-sans)", maxWidth: 280 }} className="truncate">
                      {t.subject}
                    </td>
                    <td><span className={`badge ${priorityBadge(t.priority)}`}>{t.priority}</span></td>
                    <td><span className={`badge ${statusBadge(t.status)}`}>{t.status}</span></td>
                    <td>{t.requester?.name || "—"}</td>
                    <td>{t.assignee?.name || "Unassigned"}</td>
                    <td>{formatDate(t.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {escalations.length > 0 && (
        <div className="section">
          <div className="card">
            <div className="card-header">
              <span className="card-title">Escalations</span>
              <span className="badge danger">{activeEscalations.length} active</span>
            </div>
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Account</th>
                  <th>Severity</th>
                  <th>Description</th>
                  <th>Status</th>
                  <th>Owner</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {escalations.map((e) => (
                  <tr key={e.escalation_id}>
                    <td>{e.escalation_id}</td>
                    <td>{e.account_id}</td>
                    <td><span className={`badge ${priorityBadge(e.severity)}`}>{e.severity}</span></td>
                    <td style={{ fontFamily: "var(--font-sans)", maxWidth: 280 }} className="truncate">
                      {e.description}
                    </td>
                    <td><span className={`badge ${statusBadge(e.status)}`}>{e.status}</span></td>
                    <td>{e.owner}</td>
                    <td>{formatDate(e.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {accounts.length > 0 && (
        <div className="section">
          <div className="section-title">Account Health</div>
          <div className="account-grid">
            {accounts.map((a) => (
              <div key={a.account_id} className="account-card">
                <div className="flex items-center gap-2 mb-3">
                  <span style={{ fontWeight: 600, fontSize: 14 }}>{a.company_name}</span>
                  <span className={`badge ${tierBadge(a.tier)}`}>{a.tier}</span>
                </div>
                <div className="resource-node-stats">
                  <div className="resource-node-stat">
                    <span>ARR</span>
                    <span>{formatCurrency(a.arr)}</span>
                  </div>
                  <div className="resource-node-stat">
                    <span>CSM</span>
                    <span>{a.csm}</span>
                  </div>
                  <div className="resource-node-stat">
                    <span>Renewal</span>
                    <span>{formatDate(a.renewal_date)}</span>
                  </div>
                  <div className="resource-node-stat">
                    <span>Products</span>
                    <span>{a.products?.length || 0}</span>
                  </div>
                </div>
                <div style={{ marginTop: 10 }}>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-tertiary">Health</span>
                    <span className="mono text-sm" style={{ color: healthColor(a.health_score), fontWeight: 700 }}>
                      {a.health_score}
                    </span>
                  </div>
                  <div className="progress-bar-bg" style={{ marginTop: 4 }}>
                    <div
                      className="progress-bar-fill"
                      style={{ width: `${a.health_score}%`, background: healthColor(a.health_score) }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
