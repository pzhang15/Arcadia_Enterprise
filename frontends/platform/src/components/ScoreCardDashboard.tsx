import { useEffect, useState } from "react";
import type { AggregateReport, SweepInfo } from "../types";
import { getAggregate, listSweeps } from "../api/client";

function fmt(n: number, d: number = 3): string {
  return Number.isFinite(n) ? n.toFixed(d) : "\u2014";
}

function compositeTone(v: number): string {
  if (v >= 0.75) return "success";
  if (v >= 0.4) return "warning";
  return "danger";
}

function ScoreBar({ value, tone }: { value: number; tone: string }) {
  const colors: Record<string, string> = {
    success: "var(--green)",
    warning: "var(--yellow)",
    danger: "var(--red)",
  };
  return (
    <div className="score-bar-bg">
      <div
        className="score-bar-fill"
        style={{
          width: `${Math.max(0, Math.min(100, value * 100))}%`,
          background: colors[tone] || "var(--accent)",
        }}
      />
    </div>
  );
}

export default function ScoreCardDashboard() {
  const [sweeps, setSweeps] = useState<SweepInfo[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [report, setReport] = useState<AggregateReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listSweeps()
      .then((s) => {
        setSweeps(s);
        if (s.length > 0) setSelected(`${s[0].scenario}/${s[0].sweep_id}`);
      })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!selected) return;
    const [scenario, sweepId] = selected.split("/", 2);
    setLoading(true);
    setError(null);
    getAggregate(scenario, sweepId)
      .then(setReport)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [selected]);

  if (error && !report) {
    return (
      <div>
        <h1 style={{ fontSize: 18, fontWeight: 700, marginBottom: 20 }}>
          Scorecard Dashboard
        </h1>
        <div className="empty-state">
          <div className="empty-state-icon">&#x1F4CA;</div>
          <div className="empty-state-text">
            No eval results available. Run{" "}
            <code>mirage-eval sweep --scenario &lt;name&gt;</code> to generate
            results.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-4 mb-5">
        <h1 style={{ fontSize: 18, fontWeight: 700 }}>Scorecard Dashboard</h1>
        {sweeps.length > 0 && (
          <select
            className="sweep-selector"
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            {sweeps.map((s) => (
              <option key={s.path} value={`${s.scenario}/${s.sweep_id}`}>
                {s.scenario} / {s.sweep_id}
              </option>
            ))}
          </select>
        )}
      </div>

      {loading && (
        <div className="empty-state">
          <div className="empty-state-text">Loading...</div>
        </div>
      )}

      {report && !loading && (
        <>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-label">Runs</div>
              <div className={`stat-value ${report.n_succeeded === report.n_runs ? "success" : "warning"}`}>
                {report.n_runs}
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Composite (mean)</div>
              <div className={`stat-value ${compositeTone(report.composite_mean)}`}>
                {fmt(report.composite_mean)}
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Models</div>
              <div className="stat-value">{report.models.length}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Tasks</div>
              <div className="stat-value">{report.tasks.length}</div>
            </div>
          </div>

          {/* Heatmap */}
          {report.models.length > 0 && report.tasks.length > 0 && (
            <div className="card mb-5">
              <div className="card-header">
                <span className="card-title">
                  Composite Heatmap (Model x Task)
                </span>
              </div>
              <div style={{ overflowX: "auto" }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Model</th>
                      {report.tasks.map((t) => (
                        <th key={t} style={{ textAlign: "center" }}>
                          {t}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {report.models.map((m) => (
                      <tr key={m}>
                        <td style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                          {m}
                        </td>
                        {report.tasks.map((t) => {
                          const cell = report.cell_by_model_task[m]?.[t];
                          if (!cell) return <td key={t} className="heatmap-cell">&mdash;</td>;
                          const tone = compositeTone(cell.composite_mean);
                          return (
                            <td key={t} className="heatmap-cell">
                              <span className={`heatmap-value ${tone}`}>
                                {fmt(cell.composite_mean)}
                              </span>
                              <span className="heatmap-sub">
                                {cell.n_passed_gates}/{cell.n_runs} gates &middot; ${fmt(cell.cost_usd_total, 3)}
                              </span>
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Per-run table */}
          <div className="card mb-5">
            <div className="card-header">
              <span className="card-title">Per-run Drilldown</span>
              <span className="text-sm text-tertiary">
                {report.runs.length} runs
              </span>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Task</th>
                    <th>Model</th>
                    <th>Seed</th>
                    <th style={{ textAlign: "right" }}>Composite</th>
                    <th style={{ textAlign: "right" }}>Judge</th>
                    <th style={{ textAlign: "center" }}>Gates</th>
                    <th style={{ textAlign: "right" }}>Turns</th>
                    <th style={{ textAlign: "right" }}>Cmds</th>
                    <th style={{ textAlign: "right" }}>Wall (s)</th>
                    <th style={{ textAlign: "right" }}>Cost ($)</th>
                    <th>Failures</th>
                  </tr>
                </thead>
                <tbody>
                  {report.runs.map((run, idx) => (
                    <tr key={idx}>
                      <td>
                        <span className="mono">{run.task_id}</span>
                      </td>
                      <td>{run.model}</td>
                      <td style={{ textAlign: "right" }}>{run.seed}</td>
                      <td style={{ textAlign: "right" }}>
                        <span className={`badge ${compositeTone(run.composite)}`}>
                          {fmt(run.composite)}
                        </span>
                      </td>
                      <td style={{ textAlign: "right" }}>
                        {fmt(run.judge.weighted)}
                      </td>
                      <td style={{ textAlign: "center" }}>
                        <span className={`badge ${run.passed_gates ? "success" : "danger"}`}>
                          {run.passed_gates ? "pass" : "fail"}
                        </span>
                      </td>
                      <td style={{ textAlign: "right" }}>
                        {run.trajectory.n_turns}
                      </td>
                      <td style={{ textAlign: "right" }}>
                        {run.trajectory.n_commands}
                      </td>
                      <td style={{ textAlign: "right" }}>
                        {fmt(run.trajectory.wallclock_s, 1)}
                      </td>
                      <td style={{ textAlign: "right" }}>
                        {fmt(run.trajectory.cost_usd, 4)}
                      </td>
                      <td className="text-sm text-secondary">
                        {run.failure_modes.join(", ") || "\u2014"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Failure modes */}
          {Object.keys(report.failure_modes).length > 0 && (
            <div className="card">
              <div className="card-header">
                <span className="card-title">Failure Modes</span>
              </div>
              <div className="card-body">
                <div className="score-grid">
                  {Object.entries(report.failure_modes)
                    .sort(([, a], [, b]) => b - a)
                    .map(([mode, count]) => (
                      <div key={mode} className="stat-card">
                        <div className="flex items-center gap-2 mb-3">
                          <span style={{ fontWeight: 600, fontSize: 13 }}>
                            {mode}
                          </span>
                          <span className="badge warning" style={{ marginLeft: "auto" }}>
                            {count}
                          </span>
                        </div>
                        <div className="text-sm text-secondary">
                          Triggered by {count} run{count === 1 ? "" : "s"}.
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          )}

          {/* Judge rubric for first run */}
          {report.runs.length > 0 && Object.keys(report.runs[0].judge.scores).length > 0 && (
            <div className="card" style={{ marginTop: 16 }}>
              <div className="card-header">
                <span className="card-title">
                  Judge Rubric (latest run: {report.runs[0].task_id})
                </span>
              </div>
              <div className="card-body">
                {Object.entries(report.runs[0].judge.scores).map(
                  ([name, score]) => {
                    const tone = compositeTone(score);
                    return (
                      <div key={name} className="rubric-item">
                        <div className="rubric-header">
                          <span className="rubric-name">{name}</span>
                          <span className={`rubric-score ${tone}`}>
                            {fmt(score)}
                          </span>
                        </div>
                        <ScoreBar value={score} tone={tone} />
                        {report.runs[0].judge.rationale[name] && (
                          <div className="rubric-rationale" style={{ marginTop: 4 }}>
                            {report.runs[0].judge.rationale[name]}
                          </div>
                        )}
                      </div>
                    );
                  },
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
