import asyncio
import importlib
import json
import time
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from mirage_eval.fixtures.build_snapshot import snapshot_workspace
from mirage_eval.report.aggregate import aggregate_sweep
from mirage_eval.report.canvas import write_canvas, write_compare_canvas
from mirage_eval.report.markdown import write_markdown_summary
from mirage_eval.runner.common import RunArtifacts
from mirage_eval.runner.l1_synthetic import run_l1
from mirage_eval.runner.l2_real import run_l2
from mirage_eval.scenario import ENTERPRISE_ROOT, ScenarioManifest
from mirage_eval.scorers.composite import ScoreCard, score_run
from rich.console import Console
from rich.table import Table

app = typer.Typer(add_completion=False, no_args_is_help=True)
console = Console()


def _load_env() -> None:
    load_dotenv(ENTERPRISE_ROOT / ".env")
    load_dotenv(ENTERPRISE_ROOT.parent / ".env.development")


def _new_sweep_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S", time.gmtime())


@app.command()
def seed(
    scenario: str = typer.Option(..., help="Scenario id (folder name)"),
    surface: str = typer.Option(
        "l1", help="l1 (disk seed + snapshot) or l2 (push to real services)"),
    clean: bool = typer.Option(False,
                               help="L2 only: clear l2_mapping.yaml first"),
):
    """Seed the scenario's corpus.

    L1 (default): run the scenario's seed function on local disk and
    build the snapshot tar.

    L2: push the corpus to real Slack + Google services using the
    scenario's seed_real entry point. Requires the L2 env vars.
    """
    _load_env()
    manifest = ScenarioManifest.load(scenario)
    if surface == "l1":
        seeder = manifest.get_seeder()
        target = seeder()
        console.print(f"[green]seeded[/green] -> {target}")
        snap_path = manifest.absolute_snapshot_path
        if snap_path:
            builder = manifest.get_builder("l1")
            ws = builder(session_id="fixture-build")
            out = asyncio.run(snapshot_workspace(ws, snap_path))
            console.print(f"[green]snapshot[/green] -> {out} "
                          f"({out.stat().st_size} bytes)")
        return
    if surface == "l2":
        if manifest.l2 is None or not manifest.l2.seed_real:
            raise typer.BadParameter(
                f"scenario {scenario!r} has no l2.seed_real configured")
        spec = manifest.l2.seed_real
        module_name, _, attr = spec.partition(":")
        mod = importlib.import_module(module_name)
        fn = getattr(mod, attr)
        out = fn(clean=clean)
        console.print(f"[green]l2 mapping[/green] -> {out}")
        return
    raise typer.BadParameter(f"unknown surface {surface!r}")


def _run_artifacts_dir(manifest: ScenarioManifest, sweep_id: str, task_id: str,
                       model: str, seed: int, surface: str) -> Path:
    root = manifest.absolute_results_dir / sweep_id / "runs"
    safe_model = model.replace("/", "_")
    return root / f"{surface}__{safe_model}__{task_id}__seed{seed}"


def _print_scorecard(card: ScoreCard) -> None:
    table = Table(title=f"ScoreCard - {card.task_id} - {card.model}",
                  show_lines=False)
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("composite", f"{card.composite:.3f}")
    table.add_row("passed_gates", str(card.passed_gates))
    table.add_row("programmatic_passed",
                  f"{card.programmatic.fraction_passed:.2f}")
    table.add_row("judge_weighted", f"{card.judge.weighted:.2f}")
    table.add_row("n_turns", str(card.trajectory.n_turns))
    table.add_row("n_commands", str(card.trajectory.n_commands))
    table.add_row("n_ops", str(card.trajectory.n_ops))
    table.add_row("wallclock_s", f"{card.trajectory.wallclock_s:.1f}")
    table.add_row("tokens_in/out",
                  f"{card.trajectory.tokens_in}/{card.trajectory.tokens_out}")
    table.add_row("cost_usd", f"${card.trajectory.cost_usd:.4f}")
    table.add_row("within_budget", str(card.trajectory.within_budget))
    table.add_row("failure_modes", ", ".join(card.failure_modes) or "(none)")
    if card.error:
        table.add_row("error", card.error)
    console.print(table)


async def _run_and_score(*, scenario: str, task_id: str, model: str, seed: int,
                         sweep_id: str, surface: str,
                         out_dir: Path) -> ScoreCard:
    if surface == "l1":
        artifacts: RunArtifacts = await run_l1(scenario_name=scenario,
                                               task_id=task_id,
                                               model=model,
                                               seed=seed,
                                               sweep_id=sweep_id,
                                               out_dir=out_dir)
    elif surface == "l2":
        artifacts = await run_l2(scenario_name=scenario,
                                 task_id=task_id,
                                 model=model,
                                 seed=seed,
                                 sweep_id=sweep_id,
                                 out_dir=out_dir)
    else:
        raise typer.BadParameter(f"unknown surface: {surface!r}")
    manifest = ScenarioManifest.load(scenario)
    task = manifest.load_task(task_id)
    card = await score_run(artifacts, task)
    card.write_to(out_dir)
    return card


@app.command()
def run(
    scenario: str = typer.Option(..., help="Scenario id"),
    task: str = typer.Option(..., help="Task filename stem"),
    model: str = typer.Option("gpt-5-mini", help="Model id"),
    seed: int = typer.Option(1, help="Per-run seed"),
    surface: str = typer.Option("l1", help="l1 (synthetic) or l2 (real APIs)"),
    sweep_id: Optional[str] = typer.Option(
        None, help="Sweep id (defaults to a fresh timestamp)"),
):
    """Run a single (task, model, seed) and compute its scorecard."""
    _load_env()
    sid = sweep_id or _new_sweep_id()
    manifest = ScenarioManifest.load(scenario)
    out_dir = _run_artifacts_dir(manifest, sid, task, model, seed, surface)
    console.print(f"[bold]sweep_id:[/bold] {sid}")
    console.print(f"[bold]out_dir:[/bold] {out_dir}")
    card = asyncio.run(
        _run_and_score(scenario=scenario,
                       task_id=task,
                       model=model,
                       seed=seed,
                       sweep_id=sid,
                       surface=surface,
                       out_dir=out_dir))
    _print_scorecard(card)


@app.command()
def sweep(
        scenario: str = typer.Option(..., help="Scenario id"),
        models: str = typer.Option("gpt-5-mini",
                                   help="Comma-separated model ids"),
        seeds: str = typer.Option("1", help="Comma-separated seeds"),
        tasks: Optional[str] = typer.Option(
            None,
            help="Comma-separated task stems (default: all primary tasks)"),
        include_adversarial: bool = typer.Option(
            False, help="Include tasks under adversarial/"),
        surface: str = typer.Option("l1", help="l1 or l2"),
        concurrency: int = typer.Option(
            2, help="Max concurrent runs (default 2)"),
        budget_usd: Optional[float] = typer.Option(
            None, help="Refuse to start if projected cost exceeds this"),
        yes: bool = typer.Option(False, help="Skip cost confirmation prompts"),
        sweep_id: Optional[str] = typer.Option(None),
):
    """Run a matrix of (task, model, seed) combinations."""
    _load_env()
    sid = sweep_id or _new_sweep_id()
    manifest = ScenarioManifest.load(scenario)
    model_list = [m.strip() for m in models.split(",") if m.strip()]
    seed_list = [int(s.strip()) for s in seeds.split(",") if s.strip()]
    if tasks:
        task_ids = [t.strip() for t in tasks.split(",") if t.strip()]
    else:
        task_ids = [
            p.stem for p in manifest.list_tasks(
                include_adversarial=include_adversarial)
        ]
    if not task_ids:
        raise typer.BadParameter("no tasks selected")
    matrix = [(t, m, s) for t in task_ids for m in model_list
              for s in seed_list]
    estimated_cost = 0.05 * len(matrix)
    console.print(f"[bold]sweep_id:[/bold] {sid}")
    console.print(f"[bold]matrix:[/bold] {len(matrix)} runs "
                  f"({len(task_ids)} tasks x {len(model_list)} models x "
                  f"{len(seed_list)} seeds)")
    console.print(
        f"[bold]projected cost (rough):[/bold] ~${estimated_cost:.2f}")
    if budget_usd is not None and estimated_cost > budget_usd:
        raise typer.BadParameter(
            f"projected cost ${estimated_cost:.2f} > budget ${budget_usd:.2f}")
    if not yes:
        typer.confirm("proceed?", abort=True)

    sem = asyncio.Semaphore(concurrency)

    async def _one(task_id: str, model: str, seed: int) -> ScoreCard | None:
        async with sem:
            out_dir = _run_artifacts_dir(manifest, sid, task_id, model, seed,
                                         surface)
            try:
                return await _run_and_score(scenario=scenario,
                                            task_id=task_id,
                                            model=model,
                                            seed=seed,
                                            sweep_id=sid,
                                            surface=surface,
                                            out_dir=out_dir)
            except Exception as exc:
                console.print(
                    f"[red]run failed[/red] {task_id}/{model}/{seed}: {exc}")
                return None

    async def _all() -> list[ScoreCard | None]:
        return await asyncio.gather(*(_one(t, m, s) for (t, m, s) in matrix))

    results = asyncio.run(_all())
    cards = [r for r in results if r is not None]
    sweep_dir = manifest.absolute_results_dir / sid
    sweep_dir.mkdir(parents=True, exist_ok=True)
    (sweep_dir / "sweep_metadata.json").write_text(
        json.dumps(
            {
                "sweep_id": sid,
                "scenario": scenario,
                "surface": surface,
                "models": model_list,
                "seeds": seed_list,
                "tasks": task_ids,
                "n_runs": len(matrix),
                "n_succeeded": len(cards),
            },
            indent=2))
    agg = aggregate_sweep(sweep_dir)
    (sweep_dir / "aggregate.json").write_text(
        json.dumps(agg.to_dict(), indent=2))
    write_markdown_summary(agg, sweep_dir / "SUMMARY.md")
    canvas_path = write_canvas(agg, manifest.absolute_canvas_path)
    console.print(
        f"[green]sweep complete[/green]: {len(cards)}/{len(matrix)} runs")
    console.print(f"[bold]results:[/bold] {sweep_dir}")
    console.print(f"[bold]canvas:[/bold] {canvas_path}")


@app.command()
def compare(
        scenario: str = typer.Option(..., help="Scenario id"),
        l1_sweep: str = typer.Option(..., help="L1 sweep id"),
        l2_sweep: str = typer.Option(..., help="L2 sweep id"),
):
    """Render an L1-vs-L2 comparison canvas for two existing sweeps."""
    _load_env()
    manifest = ScenarioManifest.load(scenario)
    l1_dir = manifest.absolute_results_dir / l1_sweep
    l2_dir = manifest.absolute_results_dir / l2_sweep
    if not l1_dir.exists():
        raise typer.BadParameter(f"l1 sweep dir not found: {l1_dir}")
    if not l2_dir.exists():
        raise typer.BadParameter(f"l2 sweep dir not found: {l2_dir}")
    l1_agg = aggregate_sweep(l1_dir)
    l2_agg = aggregate_sweep(l2_dir)
    out = write_compare_canvas(l1_agg, l2_agg)
    console.print(f"[green]l1-vs-l2 canvas[/green] -> {out}")


scenario_app = typer.Typer(no_args_is_help=True,
                           help="Create / inspect scenarios.")
app.add_typer(scenario_app, name="scenario")


@scenario_app.command("new")
def scenario_new(
    name: str = typer.Argument(..., help="New scenario id (folder name)"),
    template: str = typer.Option(
        "onboarding_it", help="Existing scenario to clone the skeleton from"),
):
    """Cookiecutter: copy ``scenarios/<template>/`` skeleton (no content)
    into ``scenarios/<name>/`` so a new business scenario can be filled
    in with its own seed.py, mounts.py, and tasks.
    """
    src = ENTERPRISE_ROOT / "scenarios" / template
    dst = ENTERPRISE_ROOT / "scenarios" / name
    if not src.exists():
        raise typer.BadParameter(f"template {template!r} not found at {src}")
    if dst.exists() and any(dst.iterdir()):
        raise typer.BadParameter(
            f"destination {dst} already exists and is non-empty")
    dst.mkdir(parents=True, exist_ok=True)
    (dst / "tasks").mkdir(exist_ok=True)
    (dst / "tests").mkdir(exist_ok=True)
    (dst / "fixture").mkdir(exist_ok=True)
    (dst / "__init__.py").write_text("")
    (dst / "tests" / "__init__.py").write_text("")
    (dst / "fixture" / ".gitkeep").write_text("")
    manifest = (f"id: {name}\n"
                f"name: {name.replace('_', ' ').title()} (TBD)\n"
                f"description: |\n"
                f"  TODO: describe this scenario.\n"
                f"\n"
                f"mounts:\n"
                f"  l1:\n"
                f"    builder: scenarios.{name}.mounts:build_l1_workspace\n"
                f"\n"
                f"fixture:\n"
                f"  seed: scenarios.{name}.seed:main\n"
                f"  snapshot_path: scenarios/{name}/fixture/corpus.tar\n"
                f"\n"
                f"tasks_dir: scenarios/{name}/tasks\n"
                f"results_dir: results/{name}\n"
                f"canvas_path: canvases/{name}/dashboard.canvas.tsx\n")
    (dst / "scenario.yaml").write_text(manifest)
    (dst / "README.md").write_text(
        f"# Scenario: {name}\n\n"
        f"TODO: write the scenario story, cast, and ground-truth\n"
        f"narrative. Bootstrap from the {template} scenario:\n"
        f"\n"
        f"1. Rewrite `seed.py` to generate your synthetic corpus.\n"
        f"2. Rewrite `mounts.py::build_l1_workspace` for the mounts you need.\n"
        f"3. Author tasks in `tasks/`.\n"
        f"4. Run `uv run mirage-eval seed --scenario {name}` then "
        f"`uv run mirage-eval run --scenario {name} --task <id>`.\n")
    (dst / "seed.py").write_text(
        f'"""Seed for the {name} scenario. TODO: implement."""\n'
        f"from pathlib import Path\n\n"
        f"DEFAULT_ROOT = str(\n"
        f"    (Path(__file__).resolve().parent / 'fixture' / 'disk').resolve())\n\n"
        f"def main(root=DEFAULT_ROOT, *, clean=True):\n"
        f"    target = Path(root).expanduser().resolve()\n"
        f"    target.mkdir(parents=True, exist_ok=True)\n"
        f"    return target\n")
    (dst / "mounts.py").write_text(
        f'"""Mounts for the {name} scenario. TODO: implement."""\n'
        f"from pathlib import Path\n\n"
        f"from mirage import MountMode, RAMResource, Workspace\n\n"
        f"DEFAULT_DISK_ROOT = (Path(__file__).resolve().parent / 'fixture'\n"
        f"                     / 'disk').resolve()\n\n"
        f"def build_l1_workspace(disk_root=None, *, agent_id='mirage-eval',\n"
        f"                       session_id='default'):\n"
        f"    return Workspace(\n"
        f"        {{'/': (RAMResource(), MountMode.WRITE)}},\n"
        f"        mode=MountMode.WRITE,\n"
        f"        agent_id=agent_id,\n"
        f"        session_id=session_id)\n")
    canvas_dst = ENTERPRISE_ROOT / "canvases" / name
    canvas_dst.mkdir(parents=True, exist_ok=True)
    (canvas_dst / ".gitkeep").write_text("")
    console.print(f"[green]created[/green] scenario {name!r} at {dst}")
    console.print(f"  next: edit {dst}/seed.py, {dst}/mounts.py, "
                  f"and add YAMLs under {dst}/tasks/")


@app.command()
def report(
        scenario: str = typer.Option(..., help="Scenario id"),
        sweep_id: str = typer.Option(..., help="Sweep id"),
):
    """Re-emit the aggregate + canvas + markdown for an existing sweep."""
    _load_env()
    manifest = ScenarioManifest.load(scenario)
    sweep_dir = manifest.absolute_results_dir / sweep_id
    if not sweep_dir.exists():
        raise typer.BadParameter(f"sweep dir not found: {sweep_dir}")
    agg = aggregate_sweep(sweep_dir)
    (sweep_dir / "aggregate.json").write_text(
        json.dumps(agg.to_dict(), indent=2))
    write_markdown_summary(agg, sweep_dir / "SUMMARY.md")
    canvas_path = write_canvas(agg, manifest.absolute_canvas_path)
    console.print(f"[green]report written[/green]: {sweep_dir}/SUMMARY.md")
    console.print(f"[bold]canvas:[/bold] {canvas_path}")


if __name__ == "__main__":
    app()
