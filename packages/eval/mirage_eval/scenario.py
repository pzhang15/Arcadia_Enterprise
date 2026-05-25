import importlib
from pathlib import Path
from typing import Any, Callable

import yaml
from mirage_eval.config import TaskConfig
from pydantic import BaseModel, ConfigDict, Field

EVAL_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = EVAL_ROOT.parent.parent
ENTERPRISE_ROOT = EVAL_ROOT


class MountsBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    builder: str


class MountsSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    l1: MountsBlock
    l2: MountsBlock | None = None


class FixtureSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seed: str
    snapshot_path: str


class L2ResourceSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    kind: str | list[str]
    env: list[str] = Field(default_factory=list)
    mount_as: str | None = None


class L2Section(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resources: dict[str, L2ResourceSpec]
    seed_real: str | None = None
    mapping_path: str | None = None


class ScenarioManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str
    mounts: MountsSection
    fixture: FixtureSection
    l2: L2Section | None = None
    tasks_dir: str
    results_dir: str
    canvas_path: str
    manifest_path: Path = Field(exclude=True)

    @classmethod
    def load(cls, name_or_path: str) -> "ScenarioManifest":
        """Load a scenario manifest by scenario id or absolute path.

        Args:
            name_or_path (str): Scenario id (e.g. ``onboarding_it``) or path
                to a ``scenario.yaml`` file.
        """
        path = Path(name_or_path)
        if not path.is_absolute() and not path.exists():
            path = ENTERPRISE_ROOT / "scenarios" / name_or_path / "scenario.yaml"
        if not path.exists():
            raise FileNotFoundError(f"scenario manifest not found: {path}")
        with path.open("r") as f:
            data = yaml.safe_load(f)
        data["manifest_path"] = path
        return cls.model_validate(data)

    @property
    def root(self) -> Path:
        return self.manifest_path.parent

    @property
    def absolute_snapshot_path(self) -> Path:
        return _resolve(self.fixture.snapshot_path)

    @property
    def absolute_tasks_dir(self) -> Path:
        return _resolve(self.tasks_dir)

    @property
    def absolute_results_dir(self) -> Path:
        return _resolve(self.results_dir)

    @property
    def absolute_canvas_path(self) -> Path:
        return _resolve(self.canvas_path)

    def list_tasks(self, include_adversarial: bool = False) -> list[Path]:
        """Return YAML paths for every task under this scenario.

        Args:
            include_adversarial (bool): Include the ``adversarial/``
                subfolder if True.
        """
        tasks_dir = self.absolute_tasks_dir
        out: list[Path] = []
        for p in sorted(tasks_dir.glob("*.yaml")):
            out.append(p)
        if include_adversarial:
            adv = tasks_dir / "adversarial"
            if adv.exists():
                for p in sorted(adv.glob("*.yaml")):
                    out.append(p)
        return out

    def load_task(self, task_id: str) -> TaskConfig:
        """Find and load a task YAML by stem (filename without extension).

        Args:
            task_id (str): Filename stem of the task YAML.
        """
        for p in self.list_tasks(include_adversarial=True):
            if p.stem == task_id:
                return TaskConfig.from_yaml(p)
        raise FileNotFoundError(
            f"task {task_id!r} not found under {self.absolute_tasks_dir}")

    def get_builder(self, surface: str) -> Callable[..., Any]:
        """Resolve the ``module:attr`` builder for a given surface (l1 / l2).

        Args:
            surface (str): Either ``l1`` or ``l2``.
        """
        if surface == "l1":
            spec = self.mounts.l1.builder
        elif surface == "l2":
            if self.mounts.l2 is None:
                raise ValueError(
                    f"scenario {self.id!r} has no l2 mounts builder")
            spec = self.mounts.l2.builder
        else:
            raise ValueError(f"unknown surface: {surface!r}")
        module_name, _, attr = spec.partition(":")
        if not attr:
            raise ValueError(f"builder spec {spec!r} must be 'module:attr'")
        module = importlib.import_module(module_name)
        return getattr(module, attr)

    def get_seeder(self) -> Callable[..., Any]:
        """Resolve the ``module:attr`` seed function for this scenario."""
        spec = self.fixture.seed
        module_name, _, attr = spec.partition(":")
        module = importlib.import_module(module_name)
        return getattr(module, attr)


def _resolve(rel_or_abs: str) -> Path:
    p = Path(rel_or_abs)
    if p.is_absolute():
        return p
    return (ENTERPRISE_ROOT / p).resolve()
