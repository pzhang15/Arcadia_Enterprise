from __future__ import annotations

from typing import Any, Protocol

from arcadia_store.types import Drained


class Store(Protocol):
    """Async persistence interface for the Arcadia platform.

    The single concrete implementation is SqlStore (Postgres or SQLite via
    SQLAlchemy). server.py and the eval harness depend only on this surface.
    """

    @property
    def dialect(self) -> str:
        ...

    async def init(self) -> None:
        ...

    async def close(self) -> None:
        ...

    async def write_batch(self, drained: Drained) -> None:
        ...

    async def next_seq(self, session_id: str) -> int:
        ...

    async def get_trace(self,
                        session_id: str,
                        after_seq: int = 0) -> list[dict]:
        ...

    async def get_runs(self, session_id: str) -> list[dict]:
        ...

    async def get_steps(self,
                        session_id: str,
                        run_id: str | None = None) -> list[dict]:
        ...

    async def get_tool_calls(self,
                             session_id: str,
                             run_id: str | None = None) -> list[dict]:
        ...

    async def get_vfs_ops(self,
                          session_id: str,
                          run_id: str | None = None) -> list[dict]:
        ...

    async def get_history(self, session_id: str) -> list[dict]:
        ...

    async def get_session(self, session_id: str) -> dict | None:
        ...

    async def list_sessions(self, limit: int = 200) -> list[dict]:
        ...

    async def max_stream_seq(self) -> int:
        ...

    async def query_stream_events(self,
                                  after_seq: int = 0,
                                  limit: int = 500,
                                  session: str | None = None) -> list[dict]:
        ...

    async def recent_stream_events(self, limit: int = 500) -> list[dict]:
        ...

    async def prune_stream_events(self, keep_last_n: int) -> int:
        ...

    async def upsert_investigation(self, values: dict[str,
                                                      Any]) -> dict | None:
        ...

    async def patch_investigation(self, session_id: str,
                                  fields: dict[str, Any]) -> dict | None:
        ...

    async def get_investigation(self, session_id: str) -> dict | None:
        ...

    async def list_investigations(self,
                                  status: str | None = None) -> list[dict]:
        ...

    async def delete_investigation(self, session_id: str) -> None:
        ...

    async def upsert_console_workspace(self, values: dict[str, Any]) -> None:
        ...

    async def list_console_workspaces(self) -> list[dict]:
        ...

    async def delete_console_workspace(self, ws_id: str) -> None:
        ...

    async def upsert_scorecard(self, values: dict[str, Any]) -> None:
        ...

    async def list_sweeps(self) -> list[dict]:
        ...

    async def get_scorecards(self, scenario: str, sweep_id: str) -> list[dict]:
        ...

    async def get_scorecard(self, scenario: str, sweep_id: str,
                            run_id: str) -> dict | None:
        ...

    async def upsert_sweep_aggregate(self, scenario: str, sweep_id: str,
                                     aggregate: dict) -> None:
        ...

    async def get_sweep_aggregate(self, scenario: str,
                                  sweep_id: str) -> dict | None:
        ...
