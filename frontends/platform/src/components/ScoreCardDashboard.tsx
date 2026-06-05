import { useEffect, useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Cpu,
  Layers,
  Target,
} from "lucide-react";
import type { AggregateReport, SweepInfo } from "../types";
import { getAggregate, listSweeps } from "../api/client";
import { Badge, EmptyState, StatCard } from "./ui";
import { Card, CardBody, CardHeader } from "./ui/Card";
import { cn } from "../lib/utils";

function fmt(n: number, d: number = 3): string {
  return Number.isFinite(n) ? n.toFixed(d) : "—";
}

type Tone = "success" | "warning" | "danger";

function compositeTone(v: number): Tone {
  if (v >= 0.75) return "success";
  if (v >= 0.4) return "warning";
  return "danger";
}

const TONE_TEXT: Record<Tone, string> = {
  success: "text-success",
  warning: "text-warning",
  danger: "text-danger",
};

const TONE_BG: Record<Tone, string> = {
  success: "bg-success",
  warning: "bg-warning",
  danger: "bg-danger",
};

const HEATMAP_BG: Record<Tone, string> = {
  success: "bg-success-soft",
  warning: "bg-warning-soft",
  danger: "bg-danger-soft",
};

function ScoreBar({ value, tone }: { value: number; tone: Tone }) {
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-3">
      <div
        className={cn(
          "h-full rounded-full transition-[width] duration-500",
          TONE_BG[tone],
        )}
        style={{ width: `${Math.max(0, Math.min(100, value * 100))}%` }}
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
      <div className="flex h-full flex-col">
        <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border bg-surface-1/60 px-6 backdrop-blur-md">
          <h1 className="text-[14px] font-semibold tracking-tight text-text-primary">
            Scorecard
          </h1>
          <p className="text-[11px] text-text-muted">
            Eval results, rubrics & failure modes
          </p>
        </header>
        <EmptyState
          icon={<BarChart3 size={22} />}
          title="No eval results yet"
          description={
            <>
              Run{" "}
              <code className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-[11px] text-text-primary">
                mirage-eval sweep --scenario &lt;name&gt;
              </code>{" "}
              to generate scorecards.
            </>
          }
          size="lg"
        />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border bg-surface-1/60 px-6 backdrop-blur-md">
        <div>
          <h1 className="text-[14px] font-semibold tracking-tight text-text-primary">
            Scorecard
          </h1>
          <p className="text-[11px] text-text-muted">
            Eval results, rubrics & failure modes
          </p>
        </div>
        {sweeps.length > 0 && (
          <select
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            className="ml-auto h-9 min-w-[280px] rounded-lg border border-border bg-surface-2 px-3 font-mono text-[12px] text-text-primary focus:border-accent"
          >
            {sweeps.map((s) => (
              <option key={s.path} value={`${s.scenario}/${s.sweep_id}`}>
                {s.scenario} · {s.sweep_id}
              </option>
            ))}
          </select>
        )}
      </header>

      <div className="flex-1 overflow-auto px-6 py-5">
        {loading && (
          <div className="flex items-center justify-center py-16 text-text-muted">
            <span className="mr-2 h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-r-transparent" />
            <span className="text-[13px]">Loading scorecard…</span>
          </div>
        )}

        {report && !loading && (
          <div className="mx-auto flex max-w-7xl flex-col gap-5">
            <div className="grid grid-cols-4 gap-3">
              <StatCard
                label="Runs"
                value={report.n_runs}
                icon={<CheckCircle2 size={15} />}
                tone={
                  report.n_succeeded === report.n_runs ? "success" : "warning"
                }
                hint={`${report.n_succeeded} succeeded`}
              />
              <StatCard
                label="Composite (mean)"
                value={fmt(report.composite_mean)}
                icon={<Target size={15} />}
                tone={compositeTone(report.composite_mean)}
                hint="Weighted rubric"
              />
              <StatCard
                label="Models"
                value={report.models.length}
                icon={<Cpu size={15} />}
                tone="info"
                hint="Distinct models"
              />
              <StatCard
                label="Tasks"
                value={report.tasks.length}
                icon={<Layers size={15} />}
                tone="accent"
                hint="Eval scenarios"
              />
            </div>

            {report.models.length > 0 && report.tasks.length > 0 && (
              <Card>
                <CardHeader
                  title="Composite Heatmap"
                  subtitle="Model × Task performance"
                />
                <div className="overflow-x-auto">
                  <table className="min-w-full text-[12px]">
                    <thead>
                      <tr>
                        <th className="border-b border-border bg-surface-1 px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wider text-text-muted">
                          Model
                        </th>
                        {report.tasks.map((t) => (
                          <th
                            key={t}
                            className="border-b border-border bg-surface-1 px-4 py-2.5 text-center text-[10px] font-semibold uppercase tracking-wider text-text-muted"
                          >
                            {t}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {report.models.map((m) => (
                        <tr key={m} className="border-b border-border last:border-b-0">
                          <td className="px-4 py-3 align-middle font-mono text-[12px] font-semibold text-text-primary">
                            {m}
                          </td>
                          {report.tasks.map((t) => {
                            const cell = report.cell_by_model_task[m]?.[t];
                            if (!cell)
                              return (
                                <td
                                  key={t}
                                  className="px-4 py-3 text-center text-text-faint"
                                >
                                  —
                                </td>
                              );
                            const tone = compositeTone(cell.composite_mean);
                            return (
                              <td
                                key={t}
                                className="px-3 py-2 text-center align-middle"
                              >
                                <div
                                  className={cn(
                                    "mx-auto rounded-lg px-2 py-1.5",
                                    HEATMAP_BG[tone],
                                  )}
                                >
                                  <div
                                    className={cn(
                                      "font-mono text-[14px] font-bold tabular-nums",
                                      TONE_TEXT[tone],
                                    )}
                                  >
                                    {fmt(cell.composite_mean)}
                                  </div>
                                  <div className="mt-0.5 text-[10px] text-text-muted">
                                    {cell.n_passed_gates}/{cell.n_runs} · $
                                    {fmt(cell.cost_usd_total, 2)}
                                  </div>
                                </div>
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            )}

            <Card>
              <CardHeader
                title="Per-run Drilldown"
                subtitle={`${report.runs.length} runs`}
              />
              <div className="overflow-x-auto">
                <table className="min-w-full text-[12.5px]">
                  <thead>
                    <tr>
                      {[
                        "Task",
                        "Model",
                        "Seed",
                        "Composite",
                        "Judge",
                        "Gates",
                        "Turns",
                        "Cmds",
                        "Wall (s)",
                        "Cost ($)",
                        "Failures",
                      ].map((h) => (
                        <th
                          key={h}
                          className="sticky top-0 border-b border-border bg-surface-1 px-3 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wider text-text-muted"
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {report.runs.map((run, idx) => (
                      <tr
                        key={idx}
                        className="border-b border-border hover:bg-surface-2/60"
                      >
                        <td className="px-3 py-2.5 font-mono text-[11.5px] text-text-secondary">
                          {run.task_id}
                        </td>
                        <td className="px-3 py-2.5 text-text-primary">
                          {run.model}
                        </td>
                        <td className="px-3 py-2.5 text-right font-mono text-text-muted">
                          {run.seed}
                        </td>
                        <td className="px-3 py-2.5">
                          <Badge
                            tone={compositeTone(run.composite)}
                            size="xs"
                            mono
                          >
                            {fmt(run.composite)}
                          </Badge>
                        </td>
                        <td className="px-3 py-2.5 font-mono text-text-secondary">
                          {fmt(run.judge.weighted)}
                        </td>
                        <td className="px-3 py-2.5">
                          <Badge
                            tone={run.passed_gates ? "success" : "danger"}
                            size="xs"
                          >
                            {run.passed_gates ? "pass" : "fail"}
                          </Badge>
                        </td>
                        <td className="px-3 py-2.5 font-mono text-text-muted">
                          {run.trajectory.n_turns}
                        </td>
                        <td className="px-3 py-2.5 font-mono text-text-muted">
                          {run.trajectory.n_commands}
                        </td>
                        <td className="px-3 py-2.5 font-mono text-text-muted">
                          {fmt(run.trajectory.wallclock_s, 1)}
                        </td>
                        <td className="px-3 py-2.5 font-mono text-text-muted">
                          {fmt(run.trajectory.cost_usd, 4)}
                        </td>
                        <td className="px-3 py-2.5 text-[11.5px] text-text-muted">
                          {run.failure_modes.join(", ") || "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>

            {Object.keys(report.failure_modes).length > 0 && (
              <Card>
                <CardHeader
                  title="Failure Modes"
                  subtitle="Aggregated across runs"
                  icon={<AlertTriangle size={15} />}
                />
                <CardBody>
                  <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
                    {Object.entries(report.failure_modes)
                      .sort(([, a], [, b]) => b - a)
                      .map(([mode, count]) => (
                        <div
                          key={mode}
                          className="rounded-lg border border-border bg-surface-2 p-3"
                        >
                          <div className="mb-2 flex items-center gap-2">
                            <AlertTriangle
                              size={13}
                              className="text-warning"
                            />
                            <span className="flex-1 truncate text-[12.5px] font-semibold text-text-primary">
                              {mode}
                            </span>
                            <Badge tone="warning" size="sm" mono>
                              {count}
                            </Badge>
                          </div>
                          <div className="text-[11.5px] text-text-muted">
                            Triggered by {count} run{count === 1 ? "" : "s"}
                          </div>
                        </div>
                      ))}
                  </div>
                </CardBody>
              </Card>
            )}

            {report.runs.length > 0 &&
              Object.keys(report.runs[0].judge.scores).length > 0 && (
                <Card>
                  <CardHeader
                    title="Judge Rubric"
                    subtitle={`Latest run: ${report.runs[0].task_id}`}
                  />
                  <CardBody>
                    <div className="flex flex-col gap-4">
                      {Object.entries(report.runs[0].judge.scores).map(
                        ([name, score]) => {
                          const tone = compositeTone(score);
                          return (
                            <div key={name}>
                              <div className="mb-1.5 flex items-center justify-between">
                                <span className="text-[13px] font-semibold text-text-primary">
                                  {name}
                                </span>
                                <span
                                  className={cn(
                                    "font-mono text-[13px] font-bold tabular-nums",
                                    TONE_TEXT[tone],
                                  )}
                                >
                                  {fmt(score)}
                                </span>
                              </div>
                              <ScoreBar value={score} tone={tone} />
                              {report.runs[0].judge.rationale[name] && (
                                <p className="mt-1.5 text-[11.5px] italic text-text-muted">
                                  {report.runs[0].judge.rationale[name]}
                                </p>
                              )}
                            </div>
                          );
                        },
                      )}
                    </div>
                  </CardBody>
                </Card>
              )}
          </div>
        )}
      </div>
    </div>
  );
}
