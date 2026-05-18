import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from statistics import mean, median


@dataclass
class CellSummary:
    n_runs: int = 0
    n_passed_gates: int = 0
    composite_mean: float = 0.0
    composite_max: float = 0.0
    judge_mean: float = 0.0
    cost_usd_total: float = 0.0
    wallclock_s_p95: float = 0.0
    failure_modes: dict[str, int] = field(default_factory=dict)


@dataclass
class AggregateReport:
    sweep_id: str
    scenario_id: str
    surface: str
    models: list[str]
    seeds: list[int]
    tasks: list[str]
    n_runs: int
    n_succeeded: int
    composite_mean: float
    composite_by_task: dict[str, float]
    composite_by_model: dict[str, float]
    cell_by_model_task: dict[str, dict[str, CellSummary]]
    failure_modes: dict[str, int]
    runs: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "sweep_id": self.sweep_id,
            "scenario_id": self.scenario_id,
            "surface": self.surface,
            "models": self.models,
            "seeds": self.seeds,
            "tasks": self.tasks,
            "n_runs": self.n_runs,
            "n_succeeded": self.n_succeeded,
            "composite_mean": self.composite_mean,
            "composite_by_task": self.composite_by_task,
            "composite_by_model": self.composite_by_model,
            "cell_by_model_task": {
                m: {t: asdict(c) for t, c in inner.items()}
                for m, inner in self.cell_by_model_task.items()
            },
            "failure_modes": self.failure_modes,
            "runs": self.runs,
        }


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = max(0, int(round(0.95 * (len(s) - 1))))
    return s[idx]


def _load_scorecard(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def aggregate_sweep(sweep_dir: Path) -> AggregateReport:
    """Walk ``sweep_dir/runs/*/scorecard.json`` and build the report.

    Args:
        sweep_dir (Path): Path to ``results/<scenario>/<sweep_id>``.
    """
    runs_dir = sweep_dir / "runs"
    cards: list[dict] = []
    if runs_dir.exists():
        for run_dir in sorted(runs_dir.iterdir()):
            sc = run_dir / "scorecard.json"
            if not sc.exists():
                continue
            data = _load_scorecard(sc)
            if data:
                cards.append(data)
    meta_path = sweep_dir / "sweep_metadata.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    sweep_id = meta.get("sweep_id", sweep_dir.name)
    scenario_id = meta.get("scenario", (cards[0].get("scenario_id")
                                        if cards else ""))
    surface = meta.get("surface", (cards[0].get("surface") if cards else "l1"))
    models = sorted({c["model"] for c in cards})
    seeds = sorted({c["seed"] for c in cards})
    tasks = sorted({c["task_id"] for c in cards})
    composites = [c["composite"] for c in cards]
    composite_mean = round(mean(composites), 4) if composites else 0.0
    by_task: dict[str, list[float]] = defaultdict(list)
    by_model: dict[str, list[float]] = defaultdict(list)
    cell: dict[str, dict[str, list[dict]]] = defaultdict(
        lambda: defaultdict(list))
    failure_modes: dict[str, int] = defaultdict(int)
    for c in cards:
        by_task[c["task_id"]].append(c["composite"])
        by_model[c["model"]].append(c["composite"])
        cell[c["model"]][c["task_id"]].append(c)
        for fm in c.get("failure_modes", []):
            failure_modes[fm] += 1
    composite_by_task = {k: round(mean(v), 4) for k, v in by_task.items()}
    composite_by_model = {k: round(mean(v), 4) for k, v in by_model.items()}
    cell_summaries: dict[str, dict[str, CellSummary]] = {}
    for m, by_t in cell.items():
        cell_summaries[m] = {}
        for t, lst in by_t.items():
            comps = [r["composite"] for r in lst]
            judges = [r["judge"]["weighted"] for r in lst]
            costs = [r["trajectory"]["cost_usd"] for r in lst]
            wcs = [r["trajectory"]["wallclock_s"] for r in lst]
            fms: dict[str, int] = defaultdict(int)
            for r in lst:
                for fm in r.get("failure_modes", []):
                    fms[fm] += 1
            cell_summaries[m][t] = CellSummary(
                n_runs=len(lst),
                n_passed_gates=sum(1 for r in lst if r.get("passed_gates")),
                composite_mean=round(mean(comps), 4),
                composite_max=round(max(comps), 4),
                judge_mean=round(mean(judges), 4),
                cost_usd_total=round(sum(costs), 4),
                wallclock_s_p95=round(_p95(wcs), 2),
                failure_modes=dict(fms),
            )
    return AggregateReport(
        sweep_id=sweep_id,
        scenario_id=scenario_id,
        surface=surface,
        models=models,
        seeds=seeds,
        tasks=tasks,
        n_runs=len(cards),
        n_succeeded=sum(1 for c in cards if not c.get("error")),
        composite_mean=composite_mean,
        composite_by_task=composite_by_task,
        composite_by_model=composite_by_model,
        cell_by_model_task=cell_summaries,
        failure_modes=dict(failure_modes),
        runs=cards,
    )
