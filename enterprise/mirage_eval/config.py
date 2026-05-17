from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class TrajectoryBudget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_turns: int = 30
    max_commands: int = 80
    max_wallclock_s: int = 240
    max_tokens: int = 200_000


class JudgeRubricItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weight: float
    criteria: str


class JudgeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str = "gpt-5"
    rubric: dict[str, JudgeRubricItem]


class TaskOracles(BaseModel):
    model_config = ConfigDict(extra="forbid")

    files_must_exist: list[str] = Field(default_factory=list)
    must_contain_in_file: dict[str, list[str]] = Field(default_factory=dict)
    must_not_contain_in_file: dict[str,
                                   list[str]] = Field(default_factory=dict)
    ops_must_touch_prefix: list[str] = Field(default_factory=list)
    ops_must_not_touch_prefix: list[str] = Field(default_factory=list)
    max_enoent: int = 0


class TaskConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    description: str
    prompt: str
    oracles: TaskOracles
    trajectory_budget: TrajectoryBudget = Field(
        default_factory=TrajectoryBudget)
    judge: JudgeConfig

    @classmethod
    def from_yaml(cls, path: Path) -> "TaskConfig":
        """Load a task YAML.

        Args:
            path (Path): Filesystem path to the task YAML.
        """
        with path.open("r") as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)


class ModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    temperature: float = 0.0
    seed: int | None = None
    extra: dict[str, Any] = Field(default_factory=dict)
