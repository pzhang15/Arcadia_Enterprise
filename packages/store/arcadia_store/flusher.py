from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from arcadia_store.buffer import RingEventBuffer
from arcadia_store.config import StoreConfig

if TYPE_CHECKING:
    from arcadia_store.sql_store import SqlStore

logger = logging.getLogger(__name__)


class AsyncFlusher:
    """Async background worker that periodically drains the buffer to the store.

    Mirrors the lineage BackgroundFlusher but awaits an async store. On failure it
    re-buffers the drained batch (idempotent upserts make retry safe) and never
    swallows the exception silently.

    Args:
        buffer (RingEventBuffer): Buffer to drain.
        store (SqlStore): Persistence backend.
        config (StoreConfig): Flush interval configuration.
    """

    def __init__(self, buffer: RingEventBuffer, store: "SqlStore",
                 config: StoreConfig) -> None:
        self._buffer = buffer
        self._store = store
        self._interval = config.flush_interval_seconds
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    def start(self) -> None:
        if self._task is not None:
            return
        self._stop.clear()
        self._task = asyncio.ensure_future(self._run())

    async def stop(self) -> None:
        """Stop the loop and perform a final drain."""
        if self._task is None:
            return
        self._stop.set()
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        await self._flush()

    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                await asyncio.sleep(self._interval)
            except asyncio.CancelledError:
                break
            await self._flush()

    async def _flush(self) -> None:
        d = self._buffer.drain()
        if d.is_empty():
            return
        try:
            await self._store.write_batch(d)
        except Exception:
            logger.exception("Failed to flush batch to store; re-buffering")
            self._buffer.restore(d)
