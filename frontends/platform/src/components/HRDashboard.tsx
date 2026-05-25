import { useState, useEffect } from "react";
import { fetchEmployees, fetchSheet } from "../api/client";
import type { Employee } from "../types";

interface SheetData {
  title?: string;
  rows?: Record<string, unknown>[];
  error?: string;
}

export default function HRDashboard() {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [hireTracker, setHireTracker] = useState<SheetData>({});
  const [ptoSheet, setPtoSheet] = useState<SheetData>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetchEmployees(),
      fetchSheet("SH101").catch(() => ({})),
      fetchSheet("SH104").catch(() => ({})),
    ])
      .then(([emp, hire, pto]) => {
        setEmployees(emp || []);
        setHireTracker(hire as SheetData);
        setPtoSheet(pto as SheetData);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading HR data...</div>;

  if (employees.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">👥</div>
        <div className="empty-state-text">
          No employee data found. Run <code>uv run mirage-eval seed --scenario northhill_corp</code> to generate data.
        </div>
      </div>
    );
  }

  const hireRows = hireTracker?.rows || [];
  const ptoRows = ptoSheet?.rows || [];
  const newHires = hireRows.filter((r: Record<string, unknown>) =>
    String(r.status || "").toLowerCase().includes("onboarding") ||
    String(r.status || "").toLowerCase().includes("new")
  );

  return (
    <div>
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Total Employees</div>
          <div className="stat-value">{employees.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">New Hires</div>
          <div className="stat-value" style={{ color: "var(--cyan)" }}>
            {newHires.length || hireRows.length}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">PTO Requests</div>
          <div className="stat-value warning">{ptoRows.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Departments</div>
          <div className="stat-value">
            {new Set(employees.map((e) => e.department).filter(Boolean)).size || "—"}
          </div>
        </div>
      </div>

      <div className="section">
        <div className="section-title">Employee Directory</div>
        <div className="employee-grid">
          {employees.map((emp) => (
            <div key={emp.id} className="employee-card">
              <div className="employee-name">{emp.name}</div>
              <div className="employee-title">{emp.title}</div>
              <div className="employee-email">{emp.email}</div>
              {emp.department && (
                <div style={{ marginTop: 8 }}>
                  <span className="badge info">{emp.department}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {hireRows.length > 0 && (
        <div className="section">
          <div className="card">
            <div className="card-header">
              <span className="card-title">Onboarding Tracker</span>
              <span className="badge info">{hireRows.length} entries</span>
            </div>
            <table className="data-table">
              <thead>
                <tr>
                  {Object.keys(hireRows[0]).map((k) => (
                    <th key={k}>{k.replace(/_/g, " ")}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {hireRows.map((row, i) => (
                  <tr key={i}>
                    {Object.values(row).map((v, j) => (
                      <td key={j}>{String(v ?? "—")}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {ptoRows.length > 0 && (
        <div className="section">
          <div className="card">
            <div className="card-header">
              <span className="card-title">PTO Calendar Summary</span>
              <span className="badge warning">{ptoRows.length} requests</span>
            </div>
            <table className="data-table">
              <thead>
                <tr>
                  {Object.keys(ptoRows[0]).map((k) => (
                    <th key={k}>{k.replace(/_/g, " ")}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ptoRows.map((row, i) => (
                  <tr key={i}>
                    {Object.values(row).map((v, j) => (
                      <td key={j}>{String(v ?? "—")}</td>
                    ))}
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
