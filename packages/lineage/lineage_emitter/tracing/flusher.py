from __future__ import annotations

import asyncio
import logging

from lineage_emitter.sinks.sqlite import SQLiteSpanStore
from lineage_emitter.tracing.buffer import RingBuffer
from lineage_emitter.tracing.config import TraceConfig

logger = logging.getLogger(__name__)


class BackgroundFlusher:
    """Async background worker that periodically drains the ring buffer to storage.

    Args:
        buffer (RingBuffer): The ring buffer to drain.
        store (SQLiteSpanStore): The storage backend.
        config (TraceConfig | None): Flush interval configuration.
    """

    def __init__(
        self,
        buffer: RingBuffer,
        store: SQLiteSpanStore,
        config: TraceConfig | None = None,
    ) -> None:
        self._buffer = buffer
        self._store = store
        self._interval = (config or TraceConfig()).flush_interval_seconds
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    def start(self) -> None:
        """Start the background flush loop."""
        if self._task is not None:
            return
        self._stop_event.clear()
        self._task = asyncio.ensure_future(self._run())

    async def stop(self) -> None:
        """Stop the background flush loop and perform a final drain."""
        if self._task is None:
            return
        self._stop_event.set()
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        self._flush()

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(self._interval)
            except asyncio.CancelledError:
                break
            self._flush()

    def _flush(self) -> None:
        spans = self._buffer.drain()
        if not spans:
            return
        try:
            written = self._store.write_spans(spans)
            logger.debug("Flushed %d spans to storage", written)
        except Exception:
            logger.exception("Failed to flush spans to storage")
            for span in spans:
                self._buffer.append(span)

    def flush_sync(self) -> int:
        """Synchronously drain the buffer and write to storage.

        Returns:
            int: Number of spans flushed.
        """
        spans = self._buffer.drain()
        if not spans:
            return 0
        return self._store.write_spans(spans)
