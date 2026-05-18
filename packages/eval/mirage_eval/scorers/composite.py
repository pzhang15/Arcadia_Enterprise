import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from mirage_eval.config import TaskConfig
from mirage_eval.runner.common import RunArtifacts
from mirage_eval.scorers.llm_judge import JudgeResult, judge_output
from mirage_eval.scorers.programmatic import (ProgrammaticResult,
                                              score_programmatic)
from mirage_eval.scorers.trajectory import (TrajectoryMetrics,
                                            score_trajectory)


@dataclass
class ScoreCard:
    scenario_id: str
    task_id: str
    surface: str
    model: str
    seed: int
    sweep_id: str
    passed_gates: bool
    programmatic: ProgrammaticResult
    trajectory: TrajectoryMetrics
    judge: JudgeResult
    composite: float
    failure_modes: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "task_id": self.task_id,
            "surface": self.surface,
            "model": self.model,
            "seed": self.seed,
            "sweep_id": self.sweep_id,
            "passed_gates": self.passed_gates,
            "programmatic": self.programmatic.to_dict(),
            "trajectory": self.trajectory.to_dict(),
            "judge": self.judge.to_dict(),
            "composite": self.composite,
            "failure_modes": list(self.failure_modes),
            "error": self.error,
        }

    def write_to(self, run_dir: Path) -> None:
        """Write ``scorecard.json`` into ``run_dir``.

        Args:
            run_dir (Path): Directory for this single run.
        """
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "scorecard.json").write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False))


def _failure_modes(prog: ProgrammaticResult,
                   traj: TrajectoryMetrics,
                   judge: JudgeResult,
                   artifacts: RunArtifacts) -> list[str]:
    out: list[str] = []
    for g in prog.gates:
        if g.passed:
            continue
        if g.name.startswith("file_exists:"):
            out.append("missing_output_file")
        elif g.name.startswith("must_contain:"):
            out.append("missing_citation")
        elif g.name.startswith("must_not_contain:"):
            out.append("hallucinated_or_confused_persona")
        elif g.name.startswith("ops_must_touch:"):
            out.append("unused_required_mount")
        elif g.name.startswith("ops_must_not_touch:"):
            out.append("touched_forbidden_mount")
        elif g.name == "no_enoent":
            out.append("enoent_path")
    if not traj.within_budget:
        out.append("budget_exceeded")
    if judge.error:
        out.append("judge_error")
    elif judge.weighted < 0.5:
        out.append("low_quality_judge")
    if artifacts.error:
        out.append("runner_exception")
    return sorted(set(out))


def _composite(prog: ProgrammaticResult, traj: TrajectoryMetrics,
               judge: JudgeResult) -> float:
    """Blend programmatic gates, trajectory, and judge into 0..1.

    - Programmatic gates: hard fails halve the gates contribution.
    - Trajectory: budget-compliant runs get full credit.
    - Judge: weighted rubric score.
    Composite formula: ``gate_score * (0.6 * judge + 0.4 * budget_ok)``.
    """
    gate_score = prog.fraction_passed if prog.all_passed else (
        prog.fraction_passed * 0.5)
    budget_ok = 1.0 if traj.within_budget else 0.5
    quality = 0.6 * judge.weighted + 0.4 * budget_ok
    return round(gate_score * quality, 4)


async def score_run(artifacts: RunArtifacts,
                    task: TaskConfig) -> ScoreCard:
    """Compute the full ``ScoreCard`` for one run.

    Args:
        artifacts (RunArtifacts): Captured run output.
        task (TaskConfig): Task definition.
    """
    prog = score_programmatic(artifacts, task)
    traj = score_trajectory(artifacts, task.trajectory_budget)
    judge = await judge_output(artifacts, task.judge)
    composite = _composite(prog, traj, judge)
    return ScoreCard(
        scenario_id=artifacts.scenario_id,
        task_id=artifacts.task_id,
        surface=artifacts.surface,
        model=artifacts.model,
        seed=artifacts.seed,
        sweep_id=artifacts.sweep_id,
        passed_gates=prog.all_passed,
        programmatic=prog,
        trajectory=traj,
        judge=judge,
        composite=composite,
        failure_modes=_failure_modes(prog, traj, judge, artifacts),
        error=artifacts.error,
    )
