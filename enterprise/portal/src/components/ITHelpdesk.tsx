import { useState, useEffect } from "react";
import { fetchTickets } from "../api/client";
import type { Ticket } from "../types";

const QUEUES = ["it_helpdesk", "it_access", "it_hardware"];
const STATUS_FILTERS = ["all", "open", "in_progress", "resolved", "closed"];

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

function statusBadge(s: string) {
  const map: Record<string, string> = {
    open: "warning",
    in_progress: "info",
    resolved: "success",
    closed: "neutral",
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

export default function ITHelpdesk() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    Promise.all(QUEUES.map((q) => fetchTickets(q)))
      .then((results) => setTickets(results.flat()))
      .finally(() => setLoading(false));
  }, []);

  const filtered = filter === "all"
    ? tickets
    : tickets.filter((t) => t.status?.toLowerCase() === filter);

  const openCount = tickets.filter((t) => t.status?.toLowerCase() === "open").length;
  const inProgressCount = tickets.filter((t) => t.status?.toLowerCase() === "in_progress").length;
  const resolvedCount = tickets.filter((t) => t.status?.toLowerCase() === "resolved").length;

  if (loading) return <div className="loading">Loading tickets...</div>;

  if (tickets.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">🎫</div>
        <div className="empty-state-text">
          No tickets found. Run <code>uv run mirage-eval seed --scenario acme_corp</code> to generate data.
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Total Tickets</div>
          <div className="stat-value">{tickets.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Open</div>
          <div className="stat-value warning">{openCount}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">In Progress</div>
          <div className="stat-value" style={{ color: "var(--blue)" }}>{inProgressCount}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Resolved</div>
          <div className="stat-value success">{resolvedCount}</div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">IT Helpdesk Queue</span>
          <div className="filter-bar" style={{ marginBottom: 0 }}>
            {STATUS_FILTERS.map((s) => (
              <button
                key={s}
                className={`filter-btn ${filter === s ? "active" : ""}`}
                onClick={() => setFilter(s)}
              >
                {s === "in_progress" ? "In Progress" : s.charAt(0).toUpperCase() + s.slice(1)}
              </button>
            ))}
          </div>
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
            {filtered.map((t) => (
              <>
                <tr
                  key={t.ticket_id}
                  className="expandable-row"
                  onClick={() => setExpandedId(expandedId === t.ticket_id ? null : t.ticket_id)}
                >
                  <td>{t.ticket_id}</td>
                  <td style={{ fontFamily: "var(--font-sans)", maxWidth: 300 }} className="truncate">
                    {t.subject}
                  </td>
                  <td><span className={`badge ${priorityBadge(t.priority)}`}>{t.priority}</span></td>
                  <td><span className={`badge ${statusBadge(t.status)}`}>{t.status}</span></td>
                  <td>{t.requester?.name || "—"}</td>
                  <td>{t.assignee?.name || "Unassigned"}</td>
                  <td>{formatDate(t.created_at)}</td>
                </tr>
                {expandedId === t.ticket_id && (
                  <tr key={`${t.ticket_id}-expanded`}>
                    <td colSpan={7} style={{ padding: 0 }}>
                      <div className="expanded-content">
                        <div style={{ marginBottom: 12 }}>{t.body}</div>
                        {t.tags?.length > 0 && (
                          <div className="flex gap-2 mb-3">
                            {t.tags.map((tag) => (
                              <span key={tag} className="badge neutral">{tag}</span>
                            ))}
                          </div>
                        )}
                        {t.comments?.length > 0 && (
                          <div>
                            <div className="text-sm text-tertiary mb-3" style={{ fontWeight: 600 }}>
                              Comments ({t.comments.length})
                            </div>
                            {t.comments.map((c, i) => (
                              <div key={i} className="comment">
                                <div className="comment-author">
                                  {c.author}
                                  <span className="comment-time">{formatDate(c.ts)}</span>
                                </div>
                                <div className="comment-body">{c.body}</div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
