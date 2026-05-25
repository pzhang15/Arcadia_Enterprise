from __future__ import annotations

import logging
import time
from typing import Any

from mirage.io.types import IOResult
from mirage.workspace import Workspace

from lineage_emitter.sinks.sqlite import SQLiteSpanStore
from lineage_emitter.tracing.buffer import RingBuffer
from lineage_emitter.tracing.collector import SpanCollector
from lineage_emitter.tracing.config import TraceConfig
from lineage_emitter.tracing.flusher import BackgroundFlusher
from lineage_emitter.tracing.span import SpanStatus

logger = logging.getLogger(__name__)


class TracingWorkspace:
    """Wrapper around mirage Workspace that emits hierarchical trace spans.

    Delegates all execute() calls to the underlying Workspace, then
    converts the resulting OpRecords into an OTel-compatible span tree
    and pushes it into an async-flushed ring buffer backed by SQLite.

    Args:
        workspace (Workspace): The mirage Workspace to wrap.
        config (TraceConfig | None): Tracing configuration. Defaults to
            in-memory-only tracing if db_path is None.
    """

    def __init__(
        self,
        workspace: Workspace,
        config: TraceConfig | None = None,
    ) -> None:
        self._ws = workspace
        self._config = config or TraceConfig()
        self._buffer = RingBuffer(self._config)
        self._collector = SpanCollector(self._buffer)
        self._store: SQLiteSpanStore | None = None
        self._flusher: BackgroundFlusher | None = None

        if self._config.db_path:
            self._store = SQLiteSpanStore(self._config.db_path)
            self._flusher = BackgroundFlusher(self._buffer, self._store, self._config)

    @property
    def workspace(self) -> Workspace:
        return self._ws

    @property
    def buffer(self) -> RingBuffer:
        return self._buffer

    @property
    def store(self) -> SQLiteSpanStore | None:
        return self._store

    @property
    def collector(self) -> SpanCollector:
        return self._collector

    def start(self) -> None:
        """Start the background flusher."""
        if self._flusher:
            self._flusher.start()

    async def stop(self) -> None:
        """Stop the background flusher and perform a final drain."""
        if self._flusher:
            await self._flusher.stop()

    def flush_sync(self) -> int:
        """Synchronously flush buffered spans to storage.

        Returns:
            int: Number of spans flushed.
        """
        if self._flusher:
            return self._flusher.flush_sync()
        return 0

    async def execute(self, command: str, **kwargs: Any) -> IOResult:
        """Execute a command with tracing.

        Delegates to the wrapped Workspace.execute(), then builds a span
        tree from the OpRecords produced during the call.

        Args:
            command (str): The shell command to execute.
            **kwargs: Forwarded to Workspace.execute().

        Returns:
            IOResult: The execution result from mirage.
        """
        session_id = kwargs.get("session_id", "default")
        agent_id = kwargs.get("agent_id", "default")
        start_ms = int(time.time() * 1000)

        records_before = self._get_records_offset()
        result = await self._ws.execute(command, **kwargs)
        end_ms = int(time.time() * 1000)

        new_records = self._get_new_records(records_before)
        exit_code = result.exit_code if isinstance(result, IOResult) else 0

        self._collector.build_trace(
            command=command,
            session_id=session_id,
            agent_id=agent_id,
            start_time_ms=start_ms,
            end_time_ms=end_ms,
            exit_code=exit_code,
            op_records=new_records,
        )

        return result

    def _get_records_offset(self) -> int:
        try:
            return len(self._ws.ops.records)
        except AttributeError:
            logger.warning(
                "Workspace.ops.records not available — "
                "falling back to root-span-only tracing"
            )
            return -1

    def _get_new_records(self, offset: int) -> list:
        if offset < 0:
            return []
        try:
            return list(self._ws.ops.records[offset:])
        except AttributeError:
            return []
