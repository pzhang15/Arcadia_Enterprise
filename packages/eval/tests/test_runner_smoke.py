"""End-to-end runner smoke test that does NOT call any LLM. Uses a
fake workspace_factory that returns a tiny in-memory scenario."""

import pytest
from mirage_eval.config import (JudgeConfig, JudgeRubricItem, TaskConfig,
                                TaskOracles, TrajectoryBudget)
from mirage_eval.runner.common import run_one_task


class _FakeScenario:
    id = "smoke"


class _FailureFactory:
    """Returns a real Workspace but the agent run will fail because no
    real OpenAI key/network — captured cleanly as an error string."""

    def __call__(self, *, agent_id, session_id):
        from mirage import MountMode, RAMResource, Workspace
        return Workspace({"/": (RAMResource(), MountMode.WRITE)},
                         mode=MountMode.WRITE,
                         agent_id=agent_id,
                         session_id=session_id)


@pytest.mark.asyncio
async def test_runner_completes_with_capture_even_when_agent_fails(
        monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    task = TaskConfig(id="smoke_v1",
                      description="d",
                      prompt="(unused; agent will fail without key)",
                      oracles=TaskOracles(),
                      trajectory_budget=TrajectoryBudget(max_turns=2,
                                                         max_commands=4,
                                                         max_wallclock_s=5,
                                                         max_tokens=1000),
                      judge=JudgeConfig(model="gpt-5",
                                        rubric={
                                            "x":
                                            JudgeRubricItem(weight=1.0,
                                                            criteria="c")
                                        }))
    artifacts = await run_one_task(
        scenario=_FakeScenario(),
        task=task,
        surface="l1",
        model="gpt-5-mini",
        seed=1,
        sweep_id="smoke-sweep",
        workspace_factory=_FailureFactory(),
    )
    assert artifacts.scenario_id == "smoke"
    assert artifacts.task_id == "smoke_v1"
    assert artifacts.error is not None
    assert artifacts.wallclock_s >= 0
    assert isinstance(artifacts.output_files, dict)
    assert isinstance(artifacts.sessions_jsonl, str)
