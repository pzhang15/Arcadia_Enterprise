from __future__ import annotations

import threading
from collections import deque

from arcadia_store.config import StoreConfig
from arcadia_store.types import (Drained, FeedOut, MessageRow, SessionRow,
                                 StreamEventRow)


class RingEventBuffer:
    """Thread-safe in-memory buffer drained in batches by the AsyncFlusher.

    Append-only rows (events, stream, messages, vfs_ops) use bounded deques that
    evict oldest on overflow. Upsert rows (sessions, runs, steps, tool_calls) use
    dicts keyed by primary key so repeated updates collapse to the latest value
    and never collide within a single flush batch.

    Args:
        config (StoreConfig): Buffer capacity configuration.
    """

    def __init__(self, config: StoreConfig) -> None:
        self._lock = threading.Lock()
        self._events: deque = deque(maxlen=config.event_buffer_capacity)
        self._stream: deque = deque(maxlen=config.stream_buffer_capacity)
        self._messages: deque = deque(maxlen=config.event_buffer_capacity)
        self._vfs_ops: deque = deque(maxlen=config.event_buffer_capacity)
        self._sessions: dict = {}
        self._runs: dict = {}
        self._steps: dict = {}
        self._tool_calls: dict = {}

    def put_session(self, row: SessionRow) -> None:
        with self._lock:
            self._sessions[row.id] = row

    def append_message(self, row: MessageRow) -> None:
        with self._lock:
            self._messages.append(row)

    def append_stream(self, row: StreamEventRow) -> None:
        with self._lock:
            self._stream.append(row)

    def add_feed(self, feed: FeedOut) -> None:
        """Buffer the consolidated events and derived rows from a coalescer step.

        Args:
            feed (FeedOut): Output of StreamCoalescer.feed/finalize.
        """
        with self._lock:
            self._events.extend(feed.events)
            self._vfs_ops.extend(feed.vfs_ops)
            for r in feed.runs:
                self._runs[r.run_id] = r
            for s in feed.steps:
                self._steps[s.step_id] = s
            for tc in feed.tool_calls:
                self._tool_calls[tc.tool_call_id] = tc

    def drain(self) -> Drained:
        with self._lock:
            d = Drained(
                sessions=list(self._sessions.values()),
                runs=list(self._runs.values()),
                steps=list(self._steps.values()),
                tool_calls=list(self._tool_calls.values()),
                messages=list(self._messages),
                vfs_ops=list(self._vfs_ops),
                events=list(self._events),
                stream=list(self._stream),
            )
            self._sessions.clear()
            self._runs.clear()
            self._steps.clear()
            self._tool_calls.clear()
            self._messages.clear()
            self._vfs_ops.clear()
            self._events.clear()
            self._stream.clear()
            return d

    def restore(self, d: Drained) -> None:
        """Re-buffer a drained batch after a failed flush, without clobbering newer rows.

        Args:
            d (Drained): The batch that failed to persist.
        """
        with self._lock:
            for s in d.sessions:
                self._sessions.setdefault(s.id, s)
            for r in d.runs:
                self._runs.setdefault(r.run_id, r)
            for st in d.steps:
                self._steps.setdefault(st.step_id, st)
            for tc in d.tool_calls:
                self._tool_calls.setdefault(tc.tool_call_id, tc)
            self._messages.extend(d.messages)
            self._vfs_ops.extend(d.vfs_ops)
            self._events.extend(d.events)
            self._stream.extend(d.stream)

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {
                "events_buffered": len(self._events),
                "stream_buffered": len(self._stream),
                "messages_buffered": len(self._messages),
                "vfs_ops_buffered": len(self._vfs_ops),
                "sessions_buffered": len(self._sessions),
                "runs_buffered": len(self._runs),
                "steps_buffered": len(self._steps),
                "tool_calls_buffered": len(self._tool_calls),
            }
