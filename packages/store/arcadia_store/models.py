from __future__ import annotations

from sqlalchemy import (JSON, BigInteger, Boolean, Column, Float, ForeignKey,
                        Index, Integer, MetaData, String, Table, Text)
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()

JSONCol = JSON().with_variant(JSONB(), "postgresql")
BigIntPK = BigInteger().with_variant(Integer, "sqlite")

sessions = Table(
    "sessions",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("services", JSONCol, nullable=False),
    Column("status", String(32), nullable=False),
    Column("created_at_ms", BigInteger, nullable=False),
    Column("updated_at_ms", BigInteger, nullable=False),
    Column("has_workspace", Boolean, nullable=False, default=False),
    Column("kind", String(16), nullable=False, default="agent"),
    Column("error", Text),
    Index("ix_sessions_created", "created_at_ms"),
)

messages = Table(
    "messages",
    metadata,
    Column("id", BigIntPK, primary_key=True, autoincrement=True),
    Column("session_id",
           String(64),
           ForeignKey("sessions.id", ondelete="CASCADE"),
           nullable=False),
    Column("role", String(16), nullable=False),
    Column("content", Text, nullable=False),
    Column("timestamp_ms", BigInteger, nullable=False),
    Index("ix_messages_session", "session_id", "id"),
)

agui_events = Table(
    "agui_events",
    metadata,
    Column("session_id",
           String(64),
           ForeignKey("sessions.id", ondelete="CASCADE"),
           primary_key=True),
    Column("seq", Integer, primary_key=True),
    Column("run_id", String(80)),
    Column("step_id", String(80)),
    Column("type", String(40), nullable=False),
    Column("payload", JSONCol, nullable=False),
    Column("timestamp_ms", BigInteger, nullable=False),
    Index("ix_events_run", "session_id", "run_id"),
)

runs = Table(
    "runs",
    metadata,
    Column("run_id", String(80), primary_key=True),
    Column("session_id",
           String(64),
           ForeignKey("sessions.id", ondelete="CASCADE"),
           nullable=False),
    Column("status", String(16), nullable=False),
    Column("started_at_ms", BigInteger, nullable=False),
    Column("ended_at_ms", BigInteger),
    Column("error", Text),
    Index("ix_runs_session", "session_id", "started_at_ms"),
)

steps = Table(
    "steps",
    metadata,
    Column("step_id", String(80), primary_key=True),
    Column("run_id", String(80)),
    Column("session_id",
           String(64),
           ForeignKey("sessions.id", ondelete="CASCADE"),
           nullable=False),
    Column("name", String(120), nullable=False),
    Column("status", String(16), nullable=False),
    Column("started_at_ms", BigInteger, nullable=False),
    Column("ended_at_ms", BigInteger),
    Column("reasoning", Text, nullable=False, default=""),
    Column("message_id", String(80)),
    Index("ix_steps_run", "run_id"),
)

tool_calls = Table(
    "tool_calls",
    metadata,
    Column("tool_call_id", String(80), primary_key=True),
    Column("session_id",
           String(64),
           ForeignKey("sessions.id", ondelete="CASCADE"),
           nullable=False),
    Column("run_id", String(80)),
    Column("step_id", String(80)),
    Column("tool_name", String(120), nullable=False),
    Column("args", Text, nullable=False, default=""),
    Column("result", Text),
    Column("exit_code", Integer),
    Column("status", String(16), nullable=False, default="running"),
    Column("started_at_ms", BigInteger, nullable=False),
    Column("ended_at_ms", BigInteger),
    Index("ix_tool_calls_step", "step_id"),
)

vfs_ops = Table(
    "vfs_ops",
    metadata,
    Column("id", BigIntPK, primary_key=True, autoincrement=True),
    Column("session_id",
           String(64),
           ForeignKey("sessions.id", ondelete="CASCADE"),
           nullable=False),
    Column("run_id", String(80)),
    Column("tool_call_id", String(80)),
    Column("op", String(40), nullable=False),
    Column("path", Text, nullable=False),
    Column("source", String(80), nullable=False),
    Column("bytes", BigInteger, nullable=False, default=0),
    Column("duration_ms", Integer, nullable=False, default=0),
    Column("mount_prefix", String(120)),
    Column("fingerprint", String(128)),
    Column("revision", String(128)),
    Column("timestamp_ms", BigInteger, nullable=False),
    Index("ix_vfs_session", "session_id", "timestamp_ms"),
)

stream_events = Table(
    "stream_events",
    metadata,
    Column("seq", BigInteger, primary_key=True, autoincrement=False),
    Column("type", String(40), nullable=False),
    Column("agent", String(120)),
    Column("session", String(64)),
    Column("payload", JSONCol, nullable=False),
    Column("timestamp_ms", BigInteger, nullable=False),
    Index("ix_stream_ts", "timestamp_ms"),
    Index("ix_stream_session", "session", "seq"),
)

investigations = Table(
    "investigations",
    metadata,
    Column("session_id", String(64), primary_key=True),
    Column("title", Text, nullable=False),
    Column("template_id", String(80), nullable=False),
    Column("severity", String(8), nullable=False),
    Column("status", String(24), nullable=False),
    Column("trigger", String(24), nullable=False),
    Column("trigger_ref", String(120)),
    Column("authority", String(24), nullable=False),
    Column("brief", Text),
    Column("resolution", Text),
    Column("resolved_at_ms", BigInteger),
    Column("escalated_to", String(120)),
    Column("created_at_ms", BigInteger, nullable=False),
    Column("updated_at_ms", BigInteger, nullable=False),
    Index("ix_investigations_status_updated", "status", "updated_at_ms"),
)

console_workspaces = Table(
    "console_workspaces",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("name", String(200), nullable=False),
    Column("template_id", String(80), nullable=False),
    Column("mode", String(8), nullable=False),
    Column("branch", String(120), nullable=False),
    Column("parent_id", String(64)),
    Column("pinned_backing", Text),
    Column("status", String(24), nullable=False),
    Column("error", Text),
    Column("created_at", Float, nullable=False),
    Column("mount_specs", JSONCol, nullable=False),
    Column("mounts", JSONCol, nullable=False),
    Column("promoted_keys", JSONCol, nullable=False),
    Column("snapshots", JSONCol, nullable=False),
    Column("effects_cache", JSONCol),
    Column("overlay_cache", JSONCol),
    Column("trajectory_cache", JSONCol),
)

scorecards = Table(
    "scorecards",
    metadata,
    Column("scenario_id", String(120), primary_key=True),
    Column("sweep_id", String(120), primary_key=True),
    Column("run_id", String(200), primary_key=True),
    Column("task_id", String(120), nullable=False),
    Column("surface", String(16), nullable=False),
    Column("model", String(120), nullable=False),
    Column("seed", Integer, nullable=False),
    Column("passed_gates", Boolean, nullable=False),
    Column("composite", Float, nullable=False),
    Column("failure_modes", JSONCol, nullable=False),
    Column("error", Text),
    Column("tokens", Integer),
    Column("cost_usd", Float),
    Column("judge_weighted", Float),
    Column("card_json", JSONCol, nullable=False),
    Column("created_at_ms", BigInteger, nullable=False),
    Index("ix_scorecards_sweep", "scenario_id", "sweep_id"),
    Index("ix_scorecards_model", "model"),
)

sweep_aggregates = Table(
    "sweep_aggregates",
    metadata,
    Column("scenario_id", String(120), primary_key=True),
    Column("sweep_id", String(120), primary_key=True),
    Column("aggregate_json", JSONCol, nullable=False),
    Column("created_at_ms", BigInteger, nullable=False),
)
