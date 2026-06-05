from __future__ import annotations

from dataclasses import asdict

from arcadia_store.config import StoreConfig
from arcadia_store.models import (agui_events, console_workspaces,
                                  investigations, messages, runs, scorecards,
                                  sessions, steps, stream_events,
                                  sweep_aggregates, tool_calls, vfs_ops)
from arcadia_store.types import Drained
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncEngine


class SqlStore:
    """SQLAlchemy-backed async store working on Postgres or SQLite.

    Args:
        engine (AsyncEngine): The async engine built by build_store.
        config (StoreConfig): Store configuration.
    """

    def __init__(self, engine: AsyncEngine, config: StoreConfig) -> None:
        self._engine = engine
        self._config = config
        self._dialect = engine.sync_engine.dialect.name

    @property
    def dialect(self) -> str:
        return self._dialect

    async def init(self) -> None:
        async with self._engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

    async def close(self) -> None:
        await self._engine.dispose()

    def _ins(self, table):
        if self._dialect == "postgresql":
            return pg_insert(table)
        return sqlite_insert(table)

    def _upsert(self, table, pk: list[str], update_cols: list[str]):
        ins = self._ins(table)
        return ins.on_conflict_do_update(
            index_elements=pk,
            set_={c: getattr(ins.excluded, c)
                  for c in update_cols},
        )

    def _ignore(self, table, pk: list[str]):
        return self._ins(table).on_conflict_do_nothing(index_elements=pk)

    async def write_batch(self, d: Drained) -> None:
        async with self._engine.begin() as conn:
            if d.sessions:
                await conn.execute(
                    self._upsert(sessions, ["id"], [
                        "services", "status", "created_at_ms", "updated_at_ms",
                        "has_workspace", "kind", "error"
                    ]), [asdict(r) for r in d.sessions])
            if d.runs:
                await conn.execute(
                    self._upsert(runs, ["run_id"], [
                        "session_id", "status", "started_at_ms", "ended_at_ms",
                        "error"
                    ]), [asdict(r) for r in d.runs])
            if d.steps:
                await conn.execute(
                    self._upsert(steps, ["step_id"], [
                        "run_id", "session_id", "name", "status",
                        "started_at_ms", "ended_at_ms", "reasoning",
                        "message_id"
                    ]), [asdict(r) for r in d.steps])
            if d.tool_calls:
                await conn.execute(
                    self._upsert(tool_calls, ["tool_call_id"], [
                        "session_id", "run_id", "step_id", "tool_name", "args",
                        "result", "exit_code", "status", "started_at_ms",
                        "ended_at_ms"
                    ]), [asdict(r) for r in d.tool_calls])
            if d.messages:
                await conn.execute(messages.insert(),
                                   [asdict(r) for r in d.messages])
            if d.vfs_ops:
                await conn.execute(vfs_ops.insert(),
                                   [asdict(r) for r in d.vfs_ops])
            if d.events:
                await conn.execute(
                    self._ignore(agui_events, ["session_id", "seq"]),
                    [asdict(r) for r in d.events])
            if d.stream:
                await conn.execute(self._ignore(stream_events, ["seq"]),
                                   [asdict(r) for r in d.stream])

    async def next_seq(self, session_id: str) -> int:
        async with self._engine.connect() as conn:
            res = await conn.execute(
                select(func.max(agui_events.c.seq)).where(
                    agui_events.c.session_id == session_id))
            return (res.scalar() or 0) + 1

    async def get_trace(self,
                        session_id: str,
                        after_seq: int = 0) -> list[dict]:
        async with self._engine.connect() as conn:
            res = await conn.execute(
                select(agui_events.c.payload).where(
                    agui_events.c.session_id == session_id, agui_events.c.seq
                    > after_seq).order_by(agui_events.c.seq))
            return [row[0] for row in res.all()]

    async def get_runs(self, session_id: str) -> list[dict]:
        async with self._engine.connect() as conn:
            res = await conn.execute(
                select(runs).where(runs.c.session_id == session_id).order_by(
                    runs.c.started_at_ms))
            return [dict(r._mapping) for r in res]

    async def get_steps(self,
                        session_id: str,
                        run_id: str | None = None) -> list[dict]:
        stmt = select(steps).where(steps.c.session_id == session_id)
        if run_id is not None:
            stmt = stmt.where(steps.c.run_id == run_id)
        stmt = stmt.order_by(steps.c.started_at_ms)
        async with self._engine.connect() as conn:
            res = await conn.execute(stmt)
            return [dict(r._mapping) for r in res]

    async def get_tool_calls(self,
                             session_id: str,
                             run_id: str | None = None) -> list[dict]:
        stmt = select(tool_calls).where(tool_calls.c.session_id == session_id)
        if run_id is not None:
            stmt = stmt.where(tool_calls.c.run_id == run_id)
        stmt = stmt.order_by(tool_calls.c.started_at_ms)
        async with self._engine.connect() as conn:
            res = await conn.execute(stmt)
            return [dict(r._mapping) for r in res]

    async def get_vfs_ops(self,
                          session_id: str,
                          run_id: str | None = None) -> list[dict]:
        stmt = select(vfs_ops).where(vfs_ops.c.session_id == session_id)
        if run_id is not None:
            stmt = stmt.where(vfs_ops.c.run_id == run_id)
        stmt = stmt.order_by(vfs_ops.c.timestamp_ms, vfs_ops.c.id)
        async with self._engine.connect() as conn:
            res = await conn.execute(stmt)
            return [dict(r._mapping) for r in res]

    async def get_history(self, session_id: str) -> list[dict]:
        async with self._engine.connect() as conn:
            res = await conn.execute(
                select(messages.c.role, messages.c.content,
                       messages.c.timestamp_ms).where(
                           messages.c.session_id == session_id).order_by(
                               messages.c.id))
            return [{
                "role": r.role,
                "content": r.content,
                "timestamp": (r.timestamp_ms or 0) / 1000.0
            } for r in res]

    async def get_session(self, session_id: str) -> dict | None:
        async with self._engine.connect() as conn:
            res = await conn.execute(
                select(sessions).where(sessions.c.id == session_id))
            row = res.first()
            return dict(row._mapping) if row is not None else None

    async def list_sessions(self, limit: int = 200) -> list[dict]:
        count_sq = (select(func.count()).select_from(messages).where(
            messages.c.session_id == sessions.c.id).scalar_subquery())
        last_sq = (select(messages.c.content).where(
            messages.c.session_id == sessions.c.id).order_by(
                messages.c.id.desc()).limit(1).scalar_subquery())
        stmt = (select(sessions, count_sq.label("message_count"),
                       last_sq.label("last_message")).order_by(
                           sessions.c.created_at_ms.desc()).limit(limit))
        async with self._engine.connect() as conn:
            res = await conn.execute(stmt)
            out = []
            for r in res:
                m = r._mapping
                out.append({
                    "id": m["id"],
                    "status": m["status"],
                    "services": m["services"],
                    "created_at": (m["created_at_ms"] or 0) / 1000.0,
                    "message_count": m["message_count"] or 0,
                    "last_message": (m["last_message"] or "")[:100],
                    "has_workspace": bool(m["has_workspace"]),
                })
            return out

    async def max_stream_seq(self) -> int:
        async with self._engine.connect() as conn:
            res = await conn.execute(select(func.max(stream_events.c.seq)))
            return res.scalar() or 0

    async def query_stream_events(self,
                                  after_seq: int = 0,
                                  limit: int = 500,
                                  session: str | None = None) -> list[dict]:
        stmt = select(
            stream_events.c.payload).where(stream_events.c.seq > after_seq)
        if session is not None:
            stmt = stmt.where(stream_events.c.session == session)
        stmt = stmt.order_by(stream_events.c.seq).limit(limit)
        async with self._engine.connect() as conn:
            res = await conn.execute(stmt)
            return [row[0] for row in res.all()]

    async def recent_stream_events(self, limit: int = 500) -> list[dict]:
        stmt = select(stream_events.c.payload).order_by(
            stream_events.c.seq.desc()).limit(limit)
        async with self._engine.connect() as conn:
            res = await conn.execute(stmt)
            rows = [row[0] for row in res.all()]
        rows.reverse()
        return rows

    async def prune_stream_events(self, keep_last_n: int) -> int:
        async with self._engine.begin() as conn:
            res = await conn.execute(select(func.max(stream_events.c.seq)))
            max_seq = res.scalar() or 0
            cutoff = max_seq - keep_last_n
            if cutoff <= 0:
                return 0
            dres = await conn.execute(
                delete(stream_events).where(stream_events.c.seq <= cutoff))
            return dres.rowcount or 0

    async def upsert_investigation(self, values: dict) -> dict | None:
        cols = [c for c in values if c != "session_id"]
        async with self._engine.begin() as conn:
            await conn.execute(
                self._upsert(investigations, ["session_id"], cols), [values])
        return await self.get_investigation(values["session_id"])

    async def patch_investigation(self, session_id: str,
                                  fields: dict) -> dict | None:
        if fields:
            async with self._engine.begin() as conn:
                res = await conn.execute(
                    update(investigations).where(
                        investigations.c.session_id == session_id).values(
                            **fields))
                if (res.rowcount or 0) == 0:
                    return None
        return await self.get_investigation(session_id)

    async def get_investigation(self, session_id: str) -> dict | None:
        async with self._engine.connect() as conn:
            res = await conn.execute(
                select(investigations).where(
                    investigations.c.session_id == session_id))
            row = res.first()
            return dict(row._mapping) if row is not None else None

    async def list_investigations(self,
                                  status: str | None = None) -> list[dict]:
        stmt = select(investigations)
        if status is not None:
            stmt = stmt.where(investigations.c.status == status)
        stmt = stmt.order_by(investigations.c.updated_at_ms.desc())
        async with self._engine.connect() as conn:
            res = await conn.execute(stmt)
            return [dict(r._mapping) for r in res]

    async def delete_investigation(self, session_id: str) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                delete(investigations).where(
                    investigations.c.session_id == session_id))

    async def upsert_console_workspace(self, values: dict) -> None:
        cols = [c for c in values if c != "id"]
        async with self._engine.begin() as conn:
            await conn.execute(self._upsert(console_workspaces, ["id"], cols),
                               [values])

    async def list_console_workspaces(self) -> list[dict]:
        async with self._engine.connect() as conn:
            res = await conn.execute(
                select(console_workspaces).order_by(
                    console_workspaces.c.created_at.desc()))
            return [dict(r._mapping) for r in res]

    async def delete_console_workspace(self, ws_id: str) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                delete(console_workspaces).where(
                    console_workspaces.c.id == ws_id))

    async def upsert_scorecard(self, values: dict) -> None:
        pk = ["scenario_id", "sweep_id", "run_id"]
        cols = [c for c in values if c not in pk]
        async with self._engine.begin() as conn:
            await conn.execute(self._upsert(scorecards, pk, cols), [values])

    async def list_sweeps(self) -> list[dict]:
        async with self._engine.connect() as conn:
            res = await conn.execute(
                select(scorecards.c.scenario_id,
                       scorecards.c.sweep_id).distinct())
            return [{
                "scenario": r.scenario_id,
                "sweep_id": r.sweep_id
            } for r in res]

    async def get_scorecards(self, scenario: str, sweep_id: str) -> list[dict]:
        async with self._engine.connect() as conn:
            res = await conn.execute(
                select(scorecards.c.card_json).where(
                    scorecards.c.scenario_id == scenario,
                    scorecards.c.sweep_id == sweep_id))
            return [row[0] for row in res.all()]

    async def get_scorecard(self, scenario: str, sweep_id: str,
                            run_id: str) -> dict | None:
        async with self._engine.connect() as conn:
            res = await conn.execute(
                select(scorecards.c.card_json).where(
                    scorecards.c.scenario_id == scenario,
                    scorecards.c.sweep_id == sweep_id,
                    scorecards.c.run_id == run_id))
            row = res.first()
            return row[0] if row is not None else None

    async def upsert_sweep_aggregate(self, scenario: str, sweep_id: str,
                                     aggregate: dict) -> None:
        created = int(aggregate.get("created_at_ms") or 0)
        values = {
            "scenario_id": scenario,
            "sweep_id": sweep_id,
            "aggregate_json": aggregate,
            "created_at_ms": created
        }
        async with self._engine.begin() as conn:
            await conn.execute(
                self._upsert(sweep_aggregates, ["scenario_id", "sweep_id"],
                             ["aggregate_json", "created_at_ms"]), [values])

    async def get_sweep_aggregate(self, scenario: str,
                                  sweep_id: str) -> dict | None:
        async with self._engine.connect() as conn:
            res = await conn.execute(
                select(sweep_aggregates.c.aggregate_json).where(
                    sweep_aggregates.c.scenario_id == scenario,
                    sweep_aggregates.c.sweep_id == sweep_id))
            row = res.first()
            return row[0] if row is not None else None
