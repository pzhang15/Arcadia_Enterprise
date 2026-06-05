from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionRow:
    id: str
    services: list[str]
    status: str
    created_at_ms: int
    updated_at_ms: int
    has_workspace: bool = False
    kind: str = "agent"
    error: str | None = None


@dataclass
class MessageRow:
    session_id: str
    role: str
    content: str
    timestamp_ms: int


@dataclass
class EventRow:
    session_id: str
    seq: int
    type: str
    payload: dict[str, Any]
    timestamp_ms: int
    run_id: str | None = None
    step_id: str | None = None


@dataclass
class RunRow:
    run_id: str
    session_id: str
    status: str
    started_at_ms: int
    ended_at_ms: int | None = None
    error: str | None = None


@dataclass
class StepRow:
    step_id: str
    run_id: str | None
    session_id: str
    name: str
    status: str
    started_at_ms: int
    ended_at_ms: int | None = None
    reasoning: str = ""
    message_id: str | None = None


@dataclass
class ToolCallRow:
    tool_call_id: str
    session_id: str
    run_id: str | None
    step_id: str | None
    tool_name: str
    args: str = ""
    result: str | None = None
    exit_code: int | None = None
    status: str = "running"
    started_at_ms: int = 0
    ended_at_ms: int | None = None


@dataclass
class VfsOpRow:
    session_id: str
    op: str
    path: str
    source: str
    bytes: int
    duration_ms: int
    timestamp_ms: int
    run_id: str | None = None
    tool_call_id: str | None = None
    mount_prefix: str | None = None
    fingerprint: str | None = None
    revision: str | None = None


@dataclass
class StreamEventRow:
    seq: int
    type: str
    payload: dict[str, Any]
    timestamp_ms: int
    agent: str | None = None
    session: str | None = None


@dataclass
class InvestigationRow:
    session_id: str
    title: str
    template_id: str
    severity: str
    status: str
    trigger: str
    authority: str
    created_at_ms: int
    updated_at_ms: int
    trigger_ref: str | None = None
    brief: str | None = None
    resolution: str | None = None
    resolved_at_ms: int | None = None
    escalated_to: str | None = None


@dataclass
class ConsoleWorkspaceRow:
    id: str
    name: str
    template_id: str
    mode: str
    branch: str
    status: str
    created_at: float
    mount_specs: list[Any] = field(default_factory=list)
    mounts: list[Any] = field(default_factory=list)
    promoted_keys: list[str] = field(default_factory=list)
    snapshots: list[Any] = field(default_factory=list)
    parent_id: str | None = None
    pinned_backing: str | None = None
    error: str | None = None
    effects_cache: Any = None
    overlay_cache: Any = None
    trajectory_cache: Any = None


@dataclass
class ScorecardRow:
    scenario_id: str
    sweep_id: str
    run_id: str
    task_id: str
    surface: str
    model: str
    seed: int
    passed_gates: bool
    composite: float
    failure_modes: list[str]
    card_json: dict[str, Any]
    created_at_ms: int
    error: str | None = None
    tokens: int | None = None
    cost_usd: float | None = None
    judge_weighted: float | None = None


@dataclass
class Drained:
    sessions: list[SessionRow] = field(default_factory=list)
    runs: list[RunRow] = field(default_factory=list)
    steps: list[StepRow] = field(default_factory=list)
    tool_calls: list[ToolCallRow] = field(default_factory=list)
    messages: list[MessageRow] = field(default_factory=list)
    vfs_ops: list[VfsOpRow] = field(default_factory=list)
    events: list[EventRow] = field(default_factory=list)
    stream: list[StreamEventRow] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (self.sessions or self.runs or self.steps or self.tool_calls
                    or self.messages or self.vfs_ops or self.events
                    or self.stream)


@dataclass
class FeedOut:
    events: list[EventRow] = field(default_factory=list)
    runs: list[RunRow] = field(default_factory=list)
    steps: list[StepRow] = field(default_factory=list)
    tool_calls: list[ToolCallRow] = field(default_factory=list)
    vfs_ops: list[VfsOpRow] = field(default_factory=list)
