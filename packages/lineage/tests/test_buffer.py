import pytest

from lineage_emitter.tracing.buffer import RingBuffer
from lineage_emitter.tracing.config import TraceConfig
from lineage_emitter.tracing.span import Span, SpanKind, TraceLevel


def _make_span(level: TraceLevel = TraceLevel.TRACE, start: int = 0) -> Span:
    return Span(trace_id="t1", name="test", level=level, start_time_ms=start)


def test_append_and_drain():
    buf = RingBuffer()
    s = _make_span()
    assert buf.append(s)
    drained = buf.drain()
    assert len(drained) == 1
    assert drained[0] is s


def test_drain_empties_buffer():
    buf = RingBuffer()
    buf.append(_make_span())
    buf.drain()
    assert buf.drain() == []


def test_drain_specific_level():
    buf = RingBuffer()
    buf.append(_make_span(TraceLevel.AUDIT))
    buf.append(_make_span(TraceLevel.TRACE))
    buf.append(_make_span(TraceLevel.OPERATIONAL))

    audit_spans = buf.drain(TraceLevel.AUDIT)
    assert len(audit_spans) == 1

    remaining = buf.drain()
    assert len(remaining) == 2


def test_operational_eviction():
    cfg = TraceConfig(buffer_capacity_operational=3)
    buf = RingBuffer(cfg)

    for i in range(5):
        buf.append(_make_span(TraceLevel.OPERATIONAL, start=i))

    stats = buf.stats()
    assert stats["operational_buffered"] == 3
    assert stats["operational_dropped"] == 2


def test_trace_eviction():
    cfg = TraceConfig(buffer_capacity_trace=2)
    buf = RingBuffer(cfg)

    for i in range(4):
        buf.append(_make_span(TraceLevel.TRACE, start=i))

    stats = buf.stats()
    assert stats["trace_buffered"] == 2
    assert stats["trace_dropped"] == 2


def test_audit_backpressure():
    cfg = TraceConfig(buffer_capacity_audit=2)
    buf = RingBuffer(cfg)

    assert buf.append(_make_span(TraceLevel.AUDIT))
    assert buf.append(_make_span(TraceLevel.AUDIT))
    assert not buf.append(_make_span(TraceLevel.AUDIT))

    stats = buf.stats()
    assert stats["audit_buffered"] == 2
    assert stats["audit_dropped"] == 0


def test_drain_sorted_by_start_time():
    buf = RingBuffer()
    buf.append(_make_span(TraceLevel.TRACE, start=300))
    buf.append(_make_span(TraceLevel.AUDIT, start=100))
    buf.append(_make_span(TraceLevel.OPERATIONAL, start=200))

    drained = buf.drain()
    assert [s.start_time_ms for s in drained] == [100, 200, 300]


def test_stats_initial():
    buf = RingBuffer()
    stats = buf.stats()
    assert stats["audit_buffered"] == 0
    assert stats["trace_buffered"] == 0
    assert stats["operational_buffered"] == 0
    assert stats["audit_dropped"] == 0
    assert stats["trace_dropped"] == 0
    assert stats["operational_dropped"] == 0
