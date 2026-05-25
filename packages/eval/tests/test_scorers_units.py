from mirage_eval.config import (JudgeConfig, JudgeRubricItem, TaskConfig,
                                TaskOracles, TrajectoryBudget)
from mirage_eval.runner.common import RunArtifacts, TokenUsage
from mirage_eval.scorers.composite import _composite, _failure_modes
from mirage_eval.scorers.llm_judge import JudgeResult
from mirage_eval.scorers.programmatic import (_matches_prefix,
                                              score_programmatic)
from mirage_eval.scorers.trajectory import score_trajectory


def _empty_artifacts(**overrides):
    base = dict(
        scenario_id="x",
        task_id="t",
        surface="l1",
        model="gpt-5-mini",
        seed=1,
        sweep_id="sw",
        session_id="default",
        agent_id="mirage-eval",
        prompt="p",
        final_output="",
        wallclock_s=0.0,
        usage=TokenUsage(),
        op_records=[],
        sessions_jsonl="",
        output_files={},
        started_at="2026-01-01T00:00:00Z",
    )
    base.update(overrides)
    return RunArtifacts(**base)


def test_matches_prefix_exact():
    assert _matches_prefix(["/sheets/owned/foo.json"],
                           "/sheets/owned/foo.json")


def test_matches_prefix_resource_relative():
    """Mirage's streaming reads emit resource-relative paths; we must
    still match the YAML's full virtual path."""
    assert _matches_prefix(["/owned/foo.json"], "/sheets/owned/foo.json")


def test_matches_prefix_negative():
    assert not _matches_prefix(["/slack/foo"], "/gdocs/owned/bar")


def test_programmatic_passes_when_oracles_empty():
    a = _empty_artifacts()
    task = TaskConfig(id="t",
                      description="d",
                      prompt="p",
                      oracles=TaskOracles(),
                      judge=JudgeConfig(model="gpt-5",
                                        rubric={
                                            "x":
                                            JudgeRubricItem(weight=1.0,
                                                            criteria="c")
                                        }))
    r = score_programmatic(a, task)
    assert r.all_passed
    assert r.fraction_passed >= 0.99


def test_programmatic_files_must_exist_fails_when_missing():
    a = _empty_artifacts()
    task = TaskConfig(id="t",
                      description="d",
                      prompt="p",
                      oracles=TaskOracles(files_must_exist=["/out.md"]),
                      judge=JudgeConfig(model="gpt-5",
                                        rubric={
                                            "x":
                                            JudgeRubricItem(weight=1.0,
                                                            criteria="c")
                                        }))
    r = score_programmatic(a, task)
    assert not r.all_passed


def test_trajectory_within_budget():
    a = _empty_artifacts(usage=TokenUsage(input_tokens=100, output_tokens=10))
    m = score_trajectory(a, TrajectoryBudget())
    assert m.within_budget
    assert m.tokens_in == 100
    assert m.cost_usd >= 0.0


def test_trajectory_breach_when_over_budget():
    a = _empty_artifacts(wallclock_s=1000.0)
    m = score_trajectory(a, TrajectoryBudget(max_wallclock_s=10))
    assert not m.within_budget
    assert any("max_wallclock_s" in b for b in m.budget_breaches)


def test_composite_gate_failure_halves_score():
    from mirage_eval.scorers.programmatic import GateResult, ProgrammaticResult
    prog = ProgrammaticResult(gates=[
        GateResult(name="g1", passed=True),
        GateResult(name="g2", passed=False),
    ])
    traj = score_trajectory(_empty_artifacts(), TrajectoryBudget())
    judge = JudgeResult(scores={"x": 1.0}, weighted=1.0)
    score = _composite(prog, traj, judge)
    assert score > 0
    assert score <= 0.5  # gate failure halves contribution


def test_failure_modes_tags_known_categories():
    from mirage_eval.scorers.programmatic import GateResult, ProgrammaticResult
    prog = ProgrammaticResult(gates=[
        GateResult(name="file_exists:/x.md", passed=False),
        GateResult(name="must_contain:/x.md:hello", passed=False),
    ])
    traj = score_trajectory(_empty_artifacts(), TrajectoryBudget())
    judge = JudgeResult(scores={"x": 0.3}, weighted=0.3)
    a = _empty_artifacts(error="boom")
    modes = _failure_modes(prog, traj, judge, a)
    assert "missing_output_file" in modes
    assert "missing_citation" in modes
    assert "low_quality_judge" in modes
    assert "runner_exception" in modes
