from pathlib import Path

from mirage_eval.runner.common import RunArtifacts, run_one_task
from mirage_eval.scenario import ScenarioManifest


async def run_l1(
    *,
    scenario_name: str,
    task_id: str,
    model: str,
    seed: int,
    sweep_id: str,
    out_dir: Path | None = None,
) -> RunArtifacts:
    """Restore the L1 fixture and run a single task.

    Args:
        scenario_name (str): Scenario id (e.g. ``onboarding_it``).
        task_id (str): Task filename stem.
        model (str): Model identifier.
        seed (int): Per-run seed.
        sweep_id (str): Sweep id.
        out_dir (Path | None): Output directory for run artifacts.
    """
    scenario = ScenarioManifest.load(scenario_name)
    task = scenario.load_task(task_id)
    builder = scenario.get_builder("l1")
    return await run_one_task(
        scenario=scenario,
        task=task,
        surface="l1",
        model=model,
        seed=seed,
        sweep_id=sweep_id,
        workspace_factory=builder,
        out_dir=out_dir,
    )
