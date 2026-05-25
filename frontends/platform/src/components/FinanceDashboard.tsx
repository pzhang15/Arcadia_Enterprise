import { useState, useEffect } from "react";
import { fetchExpenses, fetchPurchaseOrders, fetchBudgets } from "../api/client";
import type { Expense, PurchaseOrder, BudgetData } from "../types";

function statusBadge(s: string) {
  const map: Record<string, string> = {
    approved: "success",
    paid: "success",
    pending: "warning",
    submitted: "warning",
    rejected: "danger",
    cancelled: "danger",
    open: "info",
    processing: "info",
  };
  return map[s?.toLowerCase()] || "neutral";
}

function formatCurrency(n: number, currency = "USD") {
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(n);
}

function budgetColor(pct: number) {
  if (pct >= 90) return "var(--red)";
  if (pct >= 70) return "var(--yellow)";
  return "var(--green)";
}

export default function FinanceDashboard() {
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [pos, setPos] = useState<PurchaseOrder[]>([]);
  const [budgets, setBudgets] = useState<BudgetData>({ departments: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchExpenses(), fetchPurchaseOrders(), fetchBudgets()])
      .then(([exp, po, bud]) => {
        setExpenses(exp || []);
        setPos(po || []);
        setBudgets(bud || { departments: [] });
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading finance data...</div>;

  const hasData = expenses.length > 0 || pos.length > 0 || budgets.departments?.length > 0;
  if (!hasData) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">💰</div>
        <div className="empty-state-text">
          No finance data found. Run <code>uv run mirage-eval seed --scenario northhill_corp</code> to generate data.
        </div>
      </div>
    );
  }

  const pendingExpenses = expenses.filter((e) =>
    ["pending", "submitted"].includes(e.status?.toLowerCase())
  );
  const pendingTotal = pendingExpenses.reduce((s, e) => s + (e.amount || 0), 0);
  const openPOs = pos.filter((p) => p.status?.toLowerCase() !== "approved" && p.status?.toLowerCase() !== "paid");
  const totalBudget = budgets.departments?.reduce((s, d) => s + (d.budget || 0), 0) || 0;
  const totalSpent = budgets.departments?.reduce((s, d) => s + (d.spent || 0), 0) || 0;
  const utilizationPct = totalBudget > 0 ? Math.round((totalSpent / totalBudget) * 100) : 0;

  return (
    <div>
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Pending Expenses</div>
          <div className="stat-value warning">{formatCurrency(pendingTotal)}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Open POs</div>
          <div className="stat-value" style={{ color: "var(--blue)" }}>{openPOs.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Budget Utilization</div>
          <div className="stat-value" style={{ color: budgetColor(utilizationPct) }}>
            {utilizationPct}%
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total Budget</div>
          <div className="stat-value">{formatCurrency(totalBudget)}</div>
        </div>
      </div>

      {expenses.length > 0 && (
        <div className="section">
          <div className="card">
            <div className="card-header">
              <span className="card-title">Expense Reports</span>
              <span className="badge neutral">{expenses.length} total</span>
            </div>
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Submitter</th>
                  <th>Amount</th>
                  <th>Category</th>
                  <th>Department</th>
                  <th>Status</th>
                  <th>Submitted</th>
                </tr>
              </thead>
              <tbody>
                {expenses.map((e) => (
                  <tr key={e.expense_id}>
                    <td>{e.expense_id}</td>
                    <td style={{ fontFamily: "var(--font-sans)" }}>{e.submitter?.name || "—"}</td>
                    <td>{formatCurrency(e.amount, e.currency)}</td>
                    <td><span className="badge neutral">{e.category}</span></td>
                    <td>{e.department}</td>
                    <td><span className={`badge ${statusBadge(e.status)}`}>{e.status}</span></td>
                    <td>{e.submitted_at ? new Date(e.submitted_at).toLocaleDateString() : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {pos.length > 0 && (
        <div className="section">
          <div className="card">
            <div className="card-header">
              <span className="card-title">Purchase Orders</span>
              <span className="badge neutral">{pos.length} total</span>
            </div>
            <table className="data-table">
              <thead>
                <tr>
                  <th>PO ID</th>
                  <th>Vendor</th>
                  <th>Total</th>
                  <th>Department</th>
                  <th>Status</th>
                  <th>Approved By</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {pos.map((p) => (
                  <tr key={p.po_id}>
                    <td>{p.po_id}</td>
                    <td style={{ fontFamily: "var(--font-sans)" }}>{p.vendor}</td>
                    <td>{formatCurrency(p.total)}</td>
                    <td>{p.department}</td>
                    <td><span className={`badge ${statusBadge(p.status)}`}>{p.status}</span></td>
                    <td>{p.approved_by || "—"}</td>
                    <td>{p.created_at ? new Date(p.created_at).toLocaleDateString() : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {budgets.departments?.length > 0 && (
        <div className="section">
          <div className="section-title">Budget Summary by Department</div>
          <div className="resource-map">
            {budgets.departments.map((d) => {
              const pct = d.budget > 0 ? Math.round((d.spent / d.budget) * 100) : 0;
              return (
                <div key={d.name} className="resource-node">
                  <div className="resource-node-header">
                    <span className="resource-node-name">{d.name}</span>
                    <span className={`badge ${statusBadge(d.status)}`}>{d.status}</span>
                  </div>
                  <div className="resource-node-stats">
                    <div className="resource-node-stat">
                      <span>Budget</span>
                      <span>{formatCurrency(d.budget)}</span>
                    </div>
                    <div className="resource-node-stat">
                      <span>Spent</span>
                      <span>{formatCurrency(d.spent)}</span>
                    </div>
                    <div className="resource-node-stat">
                      <span>Remaining</span>
                      <span>{formatCurrency(d.remaining)}</span>
                    </div>
                  </div>
                  <div className="progress-bar-bg" style={{ marginTop: 10 }}>
                    <div
                      className="progress-bar-fill"
                      style={{ width: `${Math.min(pct, 100)}%`, background: budgetColor(pct) }}
                    />
                  </div>
                  <div className="text-sm text-tertiary" style={{ marginTop: 4, textAlign: "right" }}>
                    {pct}% used
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
