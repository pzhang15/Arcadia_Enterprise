import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mirage import Workspace
from mirage.observe.record import OpRecord


@dataclass
class TokenUsage:
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class RunArtifacts:
    """Everything captured from a single agent run.

    Args:
        scenario_id (str): Scenario id (e.g. ``onboarding_it``).
        task_id (str): Task id (filename stem).
        surface (str): ``l1`` or ``l2``.
        model (str): Model identifier passed to the SDK.
        seed (int): Per-run seed.
        sweep_id (str): Sweep identifier (groups runs).
        session_id (str): Per-run session id used in /.sessions/.
        agent_id (str): Agent id pinned on the workspace.
        prompt (str): Task prompt the agent received.
        final_output (str): Agent's final text output.
        wallclock_s (float): Wallclock seconds for Runner.run.
        usage (TokenUsage): Aggregated across all model responses.
        op_records (list[OpRecord]): Captured byte-transfer records.
        sessions_jsonl (str): Contents of /.sessions/<date>/<sid>.jsonl.
        output_files (dict[str, str]): Files agent wrote under / (RAM
            mount), keyed by virtual path, value = utf-8 decoded bytes.
        started_at (str): UTC ISO8601 timestamp when the run started.
    """
    scenario_id: str
    task_id: str
    surface: str
    model: str
    seed: int
    sweep_id: str
    session_id: str
    agent_id: str
    prompt: str
    final_output: str
    wallclock_s: float
    usage: TokenUsage
    op_records: list[OpRecord]
    sessions_jsonl: str
    output_files: dict[str, str]
    started_at: str
    raw_responses_count: int = 0
    error: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["op_records"] = [asdict(r) for r in self.op_records]
        d["usage"] = asdict(self.usage)
        return d

    def write_to(self, run_dir: Path) -> None:
        """Persist the artifacts to ``run_dir``.

        Args:
            run_dir (Path): Output directory for this single run.
        """
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "artifacts.json").write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False))
        (run_dir / "sessions.jsonl").write_text(self.sessions_jsonl)
        out_dir = run_dir / "output_files"
        out_dir.mkdir(exist_ok=True)
        for vpath, body in self.output_files.items():
            target = out_dir / vpath.lstrip("/").replace("/", "__")
            target.write_text(body)
        (run_dir / "final_output.txt").write_text(self.final_output)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z")


def _utc_date_folder() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


_RAM_MOUNT_EXCLUDES = ("/slack", "/sheets", "/gdocs", "/tickets", "/.sessions",
                       "/dev")


async def _capture_output_files(ws: Workspace,
                                session_id: str) -> dict[str, str]:
    """List every file the agent wrote under / (RAM mount) and return
    {path: utf8_text} for each.

    Args:
        ws (Workspace): The workspace driven by the agent.
        session_id (str): Session id to execute the listing under (must
            already exist in the workspace's session manager).
    """
    prune_clauses = " -o ".join(f"-path {p}" for p in _RAM_MOUNT_EXCLUDES)
    find_cmd = (f"find / \\( {prune_clauses} \\) -prune -o -type f -print")
    listing = await ws.execute(find_cmd, session_id=session_id)
    raw = (listing.stdout or b"")
    if isinstance(raw, bytes):
        text = raw.decode(errors="replace")
    else:
        text = str(raw)
    paths = [
        line.strip() for line in text.splitlines() if line.strip() and not any(
            line.strip().startswith(p)
            for p in _RAM_MOUNT_EXCLUDES) and line.strip() != "/"
    ]
    out: dict[str, str] = {}
    for p in paths:
        try:
            data = await ws.ops.read(p)
        except (FileNotFoundError, IsADirectoryError, PermissionError):
            continue
        try:
            out[p] = data.decode("utf-8")
        except UnicodeDecodeError:
            out[p] = f"<<binary {len(data)} bytes>>"
    return out


async def _capture_sessions_jsonl(ws: Workspace, session_id: str) -> str:
    """Read every JSONL file under ``/.sessions/`` and concatenate them.

    The workspace observer writes one file per (date, session_id). Since
    each run gets a fresh workspace with a fresh observer-RAM mount, all
    JSONL files in this workspace belong to this run.

    Args:
        ws (Workspace): Workspace whose observer wrote the journal.
        session_id (str): Session id to look up (used as the preferred
            file when present).
    """
    today = _utc_date_folder()
    preferred = f"/.sessions/{today}/{session_id}.jsonl"
    fallbacks = [
        preferred,
        f"/.sessions/{today}/default.jsonl",
    ]
    for path in fallbacks:
        try:
            data = await ws.ops.read(path)
            return data.decode("utf-8", errors="replace")
        except FileNotFoundError:
            continue
    try:
        date_dir = f"/.sessions/{today}"
        listing = await ws.ops.readdir(date_dir)
        chunks: list[str] = []
        for entry in listing:
            name = (entry["name"] if isinstance(entry, dict) else getattr(
                entry, "name", str(entry)))
            if not name.endswith(".jsonl"):
                continue
            try:
                data = await ws.ops.read(f"{date_dir}/{name}")
                chunks.append(data.decode("utf-8", errors="replace"))
            except FileNotFoundError:
                continue
        return "\n".join(chunks)
    except (FileNotFoundError, NotADirectoryError):
        return ""


def _sum_usage(raw_responses) -> TokenUsage:
    usage = TokenUsage()
    for r in raw_responses or []:
        u = getattr(r, "usage", None)
        if u is None:
            continue
        usage.requests += int(getattr(u, "requests", 0) or 0)
        usage.input_tokens += int(getattr(u, "input_tokens", 0) or 0)
        usage.output_tokens += int(getattr(u, "output_tokens", 0) or 0)
    return usage


async def run_one_task(
    *,
    scenario,
    task,
    surface: str,
    model: str,
    seed: int,
    sweep_id: str,
    workspace_factory,
    agent_id: str = "mirage-eval",
    out_dir: Path | None = None,
) -> RunArtifacts:
    """Run a single (scenario, task, surface, model, seed) combination.

    Args:
        scenario: ``ScenarioManifest`` instance.
        task: ``TaskConfig`` instance loaded from a task YAML.
        surface (str): ``l1`` or ``l2``.
        model (str): Model identifier (e.g. ``gpt-5-mini``).
        seed (int): Per-run seed.
        sweep_id (str): Sweep id grouping a set of related runs.
        workspace_factory: Callable returning a fresh ``Workspace``;
            invoked with kwargs ``agent_id`` and ``session_id``.
        agent_id (str): Agent id to pin on the workspace.
        out_dir (Path | None): If given, ``RunArtifacts.write_to`` is
            called on this directory after the run.
    """
    from agents import Runner
    from agents.run import RunConfig
    from agents.sandbox import SandboxAgent, SandboxRunConfig
    from mirage.agents.openai_agents import MirageSandboxClient

    session_id = f"{scenario.id}__{sweep_id}__{task.id}__seed{seed}"
    started_at = _utc_iso()
    # Use "default" as the workspace's session_id so that ws.execute()
    # calls without explicit session_id (notably from MirageSandboxClient)
    # resolve. Each run gets a fresh workspace + fresh observer RAM, so
    # /.sessions/<date>/default.jsonl is per-run, not shared.
    ws = workspace_factory(agent_id=agent_id, session_id="default")
    # ws.execute() internally manages its own per-command OpRecord
    # context (see mirage.observe.context). The cumulative stream lives
    # on ws.ops.records, so we snapshot indices around the agent run to
    # capture only the agent's ops (excluding our own pre/post probes).
    pre_n = len(ws.ops.records)
    final_output = ""
    error: str | None = None
    raw_responses = []
    t0 = time.time()
    try:
        client = MirageSandboxClient(ws)
        agent = SandboxAgent(
            name=f"mirage-eval/{scenario.id}/{task.id}",
            model=model,
            instructions=ws.file_prompt,
        )
        result = await Runner.run(
            agent,
            task.prompt,
            run_config=RunConfig(sandbox=SandboxRunConfig(client=client)),
            max_turns=task.trajectory_budget.max_turns,
        )
        final_output = str(result.final_output or "")
        raw_responses = list(result.raw_responses or [])
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    finally:
        wallclock = time.time() - t0
    post_n = len(ws.ops.records)
    records: list[OpRecord] = list(ws.ops.records[pre_n:post_n])
    usage = _sum_usage(raw_responses)
    output_files = await _capture_output_files(ws, "default")
    sessions_jsonl = await _capture_sessions_jsonl(ws, "default")
    artifacts = RunArtifacts(
        scenario_id=scenario.id,
        task_id=task.id,
        surface=surface,
        model=model,
        seed=seed,
        sweep_id=sweep_id,
        session_id=session_id,
        agent_id=agent_id,
        prompt=task.prompt,
        final_output=final_output,
        wallclock_s=wallclock,
        usage=usage,
        op_records=list(records),
        sessions_jsonl=sessions_jsonl,
        output_files=output_files,
        started_at=started_at,
        raw_responses_count=len(raw_responses),
        error=error,
    )
    if out_dir is not None:
        artifacts.write_to(out_dir)
    return artifacts
