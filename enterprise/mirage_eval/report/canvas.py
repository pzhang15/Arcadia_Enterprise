import json
import os
from pathlib import Path

from mirage_eval.report.aggregate import AggregateReport
from mirage_eval.scenario import ENTERPRISE_ROOT


def _workspace_slug(repo_root: Path) -> str:
    return repo_root.as_posix().lstrip("/").replace("/", "-").replace(
        "_", "-")


def resolve_canvas_dir(fallback_in_repo: Path | None = None) -> Path:
    """Return the Cursor-managed canvases directory for this workspace,
    creating in-repo fallback only if Cursor's managed dir is missing.

    Args:
        fallback_in_repo (Path | None): Optional in-repo path to use if
            the managed dir cannot be located. The IDE will not pick up
            canvases from this path, but it's useful for CI / inspection.
    """
    repo_root = ENTERPRISE_ROOT.parent
    slug = _workspace_slug(repo_root)
    managed = (Path(os.path.expanduser("~"))
               / ".cursor" / "projects" / slug / "canvases")
    if managed.parent.exists():
        managed.mkdir(parents=True, exist_ok=True)
        return managed
    if fallback_in_repo is not None:
        fallback_in_repo.mkdir(parents=True, exist_ok=True)
        return fallback_in_repo
    raise FileNotFoundError(
        f"Cursor-managed canvases dir not found at {managed}; pass "
        "fallback_in_repo to write into the repo instead.")


_HEADER = """\
import {
  Card, CardBody, CardHeader, Code, Divider, Grid, H1, H2, H3,
  Pill, Row, Stack, Stat, Table, Text,
} from 'cursor/canvas'

const REPORT = __REPORT_JSON__ as const

type Cell = {
  n_runs: number
  n_passed_gates: number
  composite_mean: number
  composite_max: number
  judge_mean: number
  cost_usd_total: number
  wallclock_s_p95: number
  failure_modes: Record<string, number>
}

type Run = {
  task_id: string
  model: string
  seed: number
  surface: string
  composite: number
  passed_gates: boolean
  failure_modes: string[]
  judge: { weighted: number }
  trajectory: {
    n_turns: number
    n_commands: number
    n_ops: number
    cache_hit_rate: number
    wallclock_s: number
    cost_usd: number
  }
  error: string | null
}

type Report = {
  sweep_id: string
  scenario_id: string
  surface: string
  models: string[]
  seeds: number[]
  tasks: string[]
  n_runs: number
  n_succeeded: number
  composite_mean: number
  composite_by_task: Record<string, number>
  composite_by_model: Record<string, number>
  cell_by_model_task: Record<string, Record<string, Cell>>
  failure_modes: Record<string, number>
  runs: Run[]
}

const fmt = (n: number, d: number = 3) =>
  Number.isFinite(n) ? n.toFixed(d) : '—'

const compositeTone = (v: number) => {
  if (v >= 0.75) return 'success'
  if (v >= 0.4)  return 'warning'
  return 'danger'
}

export default function Dashboard() {
  const r = REPORT as unknown as Report

  if (r.n_runs === 0) {
    return (
      <Stack gap={20}>
        <H1>Mirage Eval — {r.scenario_id || 'no sweep yet'}</H1>
        <Text tone="secondary">
          No runs found. Run <Code>mirage-eval sweep --scenario {r.scenario_id || '<scenario>'}</Code>
          {' '}to populate this dashboard.
        </Text>
      </Stack>
    )
  }

  const failures = Object.entries(r.failure_modes).sort((a, b) => b[1] - a[1])

  const heatmapHeaders = ['Model', ...r.tasks]
  const heatmapRows = r.models.map(m => {
    const row: unknown[] = [m]
    for (const t of r.tasks) {
      const cell = r.cell_by_model_task[m]?.[t]
      if (!cell) {
        row.push('—')
        continue
      }
      row.push(
        <Stack gap={2}>
          <Pill tone={compositeTone(cell.composite_mean)} active>
            {fmt(cell.composite_mean)}
          </Pill>
          <Text size="small" tone="tertiary">
            {cell.n_passed_gates}/{cell.n_runs} gates · ${fmt(cell.cost_usd_total, 3)}
          </Text>
        </Stack>,
      )
    }
    return row as never[]
  })

  const runHeaders = [
    'task', 'model', 'seed', 'composite', 'judge', 'gates',
    'turns', 'cmds', 'ops', 'wall (s)', 'cost ($)', 'failure modes',
  ]
  const runRows = r.runs.map(run => ([
    <Code>{run.task_id}</Code>,
    run.model,
    String(run.seed),
    <Pill tone={compositeTone(run.composite)} active>{fmt(run.composite)}</Pill>,
    fmt(run.judge.weighted),
    run.passed_gates
      ? <Pill tone="success" active>pass</Pill>
      : <Pill tone="danger" active>fail</Pill>,
    String(run.trajectory.n_turns),
    String(run.trajectory.n_commands),
    String(run.trajectory.n_ops),
    fmt(run.trajectory.wallclock_s, 1),
    fmt(run.trajectory.cost_usd, 4),
    <Text size="small" tone="secondary">
      {run.failure_modes.join(', ') || '—'}
    </Text>,
  ] as never[]))
  const runRowTones = r.runs.map(run =>
    run.error ? 'danger' as const :
    run.passed_gates ? undefined :
    'warning' as const)

  return (
    <Stack gap={20}>
      <Stack gap={4}>
        <H1>Mirage Eval — {r.scenario_id}</H1>
        <Text tone="secondary" size="small">
          surface <Code>{r.surface}</Code> · sweep <Code>{r.sweep_id}</Code>
        </Text>
      </Stack>

      <Grid columns={4} gap={16}>
        <Stat value={String(r.n_runs)} label="Runs"
              tone={r.n_succeeded === r.n_runs ? 'success' : 'warning'} />
        <Stat value={fmt(r.composite_mean)} label="Composite (mean)"
              tone={compositeTone(r.composite_mean)} />
        <Stat value={String(r.models.length)} label="Models" />
        <Stat value={String(r.tasks.length)} label="Tasks" />
      </Grid>

      <Divider />

      <H2>Composite heatmap (model × task)</H2>
      <Table headers={heatmapHeaders} rows={heatmapRows} striped />

      <Divider />

      <H2>Per-run drilldown</H2>
      <Table
        headers={runHeaders}
        rows={runRows}
        rowTone={runRowTones}
        columnAlign={[
          'left','left','right','right','right','center',
          'right','right','right','right','right','left',
        ]}
        stickyHeader
        striped
      />

      {failures.length > 0 && (
        <>
          <Divider />
          <H2>Failure modes</H2>
          <H3>Count across all runs</H3>
          <Grid columns={3} gap={12}>
            {failures.map(([mode, count]) => (
              <Card key={mode}>
                <CardHeader trailing={<Pill tone="warning" active>{count}</Pill>}>
                  {mode}
                </CardHeader>
                <CardBody>
                  <Text size="small" tone="secondary">
                    Triggered by {count} run{count === 1 ? '' : 's'} this sweep.
                  </Text>
                </CardBody>
              </Card>
            ))}
          </Grid>
        </>
      )}
    </Stack>
  )
}
"""


def _payload(report: AggregateReport) -> str:
    return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)


def _stub_payload(scenario_id: str) -> str:
    """Empty-state payload for the Phase 1.10 stub.

    Args:
        scenario_id (str): Scenario id to display in the empty state.
    """
    return json.dumps({
        "sweep_id": "(none)",
        "scenario_id": scenario_id,
        "surface": "l1",
        "models": [],
        "seeds": [],
        "tasks": [],
        "n_runs": 0,
        "n_succeeded": 0,
        "composite_mean": 0.0,
        "composite_by_task": {},
        "composite_by_model": {},
        "cell_by_model_task": {},
        "failure_modes": {},
        "runs": [],
    }, indent=2)


def write_canvas(report: AggregateReport, target: Path) -> Path:
    """Render the aggregate as a Cursor canvas (.canvas.tsx) in the
    Cursor-managed canvases directory.

    The ``target`` argument's filename is preserved; its parent directory
    is replaced by the workspace's managed canvases directory.

    Args:
        report (AggregateReport): Aggregated sweep results.
        target (Path): Filename hint (e.g.
            ``canvases/onboarding_it/dashboard.canvas.tsx``); only the
            stem is used to derive the managed-dir filename.
    """
    fallback = ENTERPRISE_ROOT / "canvases" / report.scenario_id
    canvas_dir = resolve_canvas_dir(fallback_in_repo=fallback)
    filename = f"{report.scenario_id}-dashboard.canvas.tsx"
    out = canvas_dir / filename
    out.write_text(_HEADER.replace("__REPORT_JSON__", _payload(report)))
    return out


def write_stub_canvas(scenario_id: str) -> Path:
    """Write an empty-state canvas for a scenario that hasn't run yet.

    Args:
        scenario_id (str): Scenario id (e.g. ``onboarding_it``).
    """
    fallback = ENTERPRISE_ROOT / "canvases" / scenario_id
    canvas_dir = resolve_canvas_dir(fallback_in_repo=fallback)
    filename = f"{scenario_id}-dashboard.canvas.tsx"
    out = canvas_dir / filename
    out.write_text(_HEADER.replace("__REPORT_JSON__",
                                   _stub_payload(scenario_id)))
    return out


_COMPARE_HEADER = """\
import {
  Card, CardBody, CardHeader, Code, Divider, Grid, H1, H2, H3,
  Pill, Stack, Stat, Table, Text,
} from 'cursor/canvas'

const COMPARE = __COMPARE_JSON__ as const

type CellSummary = {
  composite_mean: number
  judge_mean: number
  cost_usd_total: number
  wallclock_s_p95: number
  n_runs: number
  n_passed_gates: number
}

type Side = {
  sweep_id: string
  surface: string
  composite_mean: number
  cell_by_model_task: Record<string, Record<string, CellSummary>>
}

type Compare = {
  scenario_id: string
  l1: Side
  l2: Side
  models: string[]
  tasks: string[]
}

const fmt = (n: number, d: number = 3) =>
  Number.isFinite(n) ? n.toFixed(d) : '—'

const deltaTone = (d: number) => {
  if (Math.abs(d) < 0.05) return 'neutral'
  return d >= 0 ? 'success' : 'danger'
}

export default function L1vsL2() {
  const r = COMPARE as unknown as Compare
  const headers = ['Model · Task', 'L1', 'L2', 'Δ composite',
                   'L1 cost', 'L2 cost', 'L1 wall p95', 'L2 wall p95']
  const rows: unknown[][] = []
  for (const m of r.models) {
    for (const t of r.tasks) {
      const l1 = r.l1.cell_by_model_task[m]?.[t]
      const l2 = r.l2.cell_by_model_task[m]?.[t]
      if (!l1 && !l2) continue
      const delta = (l2?.composite_mean ?? 0) - (l1?.composite_mean ?? 0)
      rows.push([
        <Stack gap={2}>
          <Text weight="semibold">{m}</Text>
          <Text size="small" tone="tertiary">{t}</Text>
        </Stack>,
        l1 ? <Pill active>{fmt(l1.composite_mean)}</Pill> : '—',
        l2 ? <Pill active>{fmt(l2.composite_mean)}</Pill> : '—',
        <Pill tone={deltaTone(delta)} active>
          {(delta >= 0 ? '+' : '') + fmt(delta)}
        </Pill>,
        l1 ? `$${fmt(l1.cost_usd_total, 3)}` : '—',
        l2 ? `$${fmt(l2.cost_usd_total, 3)}` : '—',
        l1 ? `${fmt(l1.wallclock_s_p95, 1)}s` : '—',
        l2 ? `${fmt(l2.wallclock_s_p95, 1)}s` : '—',
      ] as never[])
    }
  }
  const overallDelta = r.l2.composite_mean - r.l1.composite_mean
  return (
    <Stack gap={20}>
      <Stack gap={4}>
        <H1>L1 vs L2 — {r.scenario_id}</H1>
        <Text tone="secondary" size="small">
          L1 sweep <Code>{r.l1.sweep_id}</Code> · L2 sweep <Code>{r.l2.sweep_id}</Code>
        </Text>
      </Stack>
      <Grid columns={3} gap={16}>
        <Stat value={fmt(r.l1.composite_mean)} label="L1 composite mean" />
        <Stat value={fmt(r.l2.composite_mean)} label="L2 composite mean" />
        <Stat value={(overallDelta >= 0 ? '+' : '') + fmt(overallDelta)}
              label="Δ composite (L2 - L1)"
              tone={deltaTone(overallDelta) as 'success' | 'danger' | undefined} />
      </Grid>
      <Divider />
      <H2>Per-cell comparison</H2>
      <Table headers={headers} rows={rows as never[][]}
             columnAlign={['left','right','right','right',
                           'right','right','right','right']}
             striped />
    </Stack>
  )
}
"""


def write_compare_canvas(l1: AggregateReport, l2: AggregateReport) -> Path:
    """Render an L1-vs-L2 comparison canvas.

    Args:
        l1 (AggregateReport): L1 sweep aggregate.
        l2 (AggregateReport): L2 sweep aggregate.
    """
    if l1.scenario_id != l2.scenario_id:
        raise ValueError(
            f"scenario mismatch: l1={l1.scenario_id} l2={l2.scenario_id}")
    fallback = ENTERPRISE_ROOT / "canvases" / l1.scenario_id
    canvas_dir = resolve_canvas_dir(fallback_in_repo=fallback)
    filename = f"{l1.scenario_id}-l1-vs-l2.canvas.tsx"
    out = canvas_dir / filename

    def _side(rep: AggregateReport) -> dict:
        return {
            "sweep_id": rep.sweep_id,
            "surface": rep.surface,
            "composite_mean": rep.composite_mean,
            "cell_by_model_task": {
                m: {t: {
                    "composite_mean": c.composite_mean,
                    "judge_mean": c.judge_mean,
                    "cost_usd_total": c.cost_usd_total,
                    "wallclock_s_p95": c.wallclock_s_p95,
                    "n_runs": c.n_runs,
                    "n_passed_gates": c.n_passed_gates,
                } for t, c in inner.items()}
                for m, inner in rep.cell_by_model_task.items()
            },
        }

    payload = json.dumps({
        "scenario_id": l1.scenario_id,
        "l1": _side(l1),
        "l2": _side(l2),
        "models": sorted(set(l1.models) | set(l2.models)),
        "tasks": sorted(set(l1.tasks) | set(l2.tasks)),
    }, indent=2)
    out.write_text(_COMPARE_HEADER.replace("__COMPARE_JSON__", payload))
    return out
