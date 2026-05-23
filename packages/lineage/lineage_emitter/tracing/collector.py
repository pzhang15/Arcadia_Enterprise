from __future__ import annotations

import uuid

from mirage.observe.record import OpRecord

from lineage_emitter.tracing.buffer import RingBuffer
from lineage_emitter.tracing.span import (
    Span,
    SpanKind,
    SpanMetrics,
    SpanStatus,
    TraceLevel,
)

_READ_OPS = frozenset({"read", "readdir", "stat", "read_stream"})
_WRITE_OPS = frozenset({"write", "write_stream"})


class SpanCollector:
    """Builds hierarchical span trees from mirage OpRecords.

    Creates a root span for each execute() call and flat child spans
    from the OpRecords produced during that call. Finished span trees
    are pushed into the ring buffer.

    Args:
        buffer (RingBuffer): Destination for completed span trees.
    """

    def __init__(self, buffer: RingBuffer) -> None:
        self._buffer = buffer

    def build_trace(
        self,
        command: str,
        session_id: str,
        agent_id: str,
        start_time_ms: int,
        end_time_ms: int,
        exit_code: int,
        op_records: list[OpRecord],
    ) -> Span:
        """Build a complete trace from a finished execute() call.

        Creates a root AUDIT span and TRACE-level child spans from OpRecords,
        then pushes all spans into the ring buffer.

        Args:
            command (str): The shell command that was executed.
            session_id (str): Agent session identifier.
            agent_id (str): Agent identifier.
            start_time_ms (int): When execute() started (epoch ms).
            end_time_ms (int): When execute() finished (epoch ms).
            exit_code (int): The command's exit code.
            op_records (list[OpRecord]): OpRecords produced during execution.

        Returns:
            Span: The root span (already pushed to buffer).
        """
        trace_id = uuid.uuid4().hex

        aggregate = SpanMetrics()
        for rec in op_records:
            if rec.op in _READ_OPS:
                aggregate.bytes_read += rec.bytes
            elif rec.op in _WRITE_OPS:
                aggregate.bytes_written += rec.bytes
            aggregate.api_calls += 0 if rec.is_cache else 1
            if rec.is_cache:
                aggregate.cache_hits += 1
            else:
                aggregate.cache_misses += 1

        root_status = SpanStatus.OK if exit_code == 0 else SpanStatus.ERROR
        root = Span(
            trace_id=trace_id,
            name="execute",
            kind=SpanKind.ROOT,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
            status=root_status,
            attributes={
                "command": command,
                "exit_code": exit_code,
                "op_count": len(op_records),
            },
            metrics=aggregate,
            level=TraceLevel.AUDIT,
            session_id=session_id,
            agent_id=agent_id,
        )

        children = _build_child_spans(trace_id, root.span_id, session_id, agent_id, op_records)

        self._buffer.append(root)
        for child in children:
            self._buffer.append(child)

        return root


def _build_child_spans(
    trace_id: str,
    parent_span_id: str,
    session_id: str,
    agent_id: str,
    op_records: list[OpRecord],
) -> list[Span]:
    """Convert OpRecords into TRACE-level child spans.

    Args:
        trace_id (str): Shared trace identifier.
        parent_span_id (str): The root span's ID.
        session_id (str): Agent session identifier.
        agent_id (str): Agent identifier.
        op_records (list[OpRecord]): Records from the execute() call.

    Returns:
        list[Span]: One child span per OpRecord.
    """
    children: list[Span] = []
    for rec in op_records:
        end_ms = rec.timestamp + rec.duration_ms
        metrics = SpanMetrics()
        if rec.op in _READ_OPS:
            metrics.bytes_read = rec.bytes
        elif rec.op in _WRITE_OPS:
            metrics.bytes_written = rec.bytes
        if rec.is_cache:
            metrics.cache_hits = 1
        else:
            metrics.cache_misses = 1
            metrics.api_calls = 1

        attrs: dict[str, str | int | float | bool] = {
            "op": rec.op,
            "path": rec.path,
            "source": rec.source,
            "bytes": rec.bytes,
            "cache_hit": rec.is_cache,
            "mount_prefix": rec.mount_prefix,
        }
        if rec.fingerprint:
            attrs["fingerprint"] = rec.fingerprint
        if rec.revision:
            attrs["revision"] = rec.revision

        child = Span(
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            name=rec.op,
            kind=SpanKind.CLIENT,
            start_time_ms=rec.timestamp,
            end_time_ms=end_ms,
            status=SpanStatus.OK,
            attributes=attrs,
            metrics=metrics,
            level=TraceLevel.TRACE,
            session_id=session_id,
            agent_id=agent_id,
        )
        children.append(child)
    return children
