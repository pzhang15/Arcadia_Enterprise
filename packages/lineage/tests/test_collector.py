from lineage_emitter.tracing.buffer import RingBuffer
from lineage_emitter.tracing.collector import SpanCollector
from lineage_emitter.tracing.span import SpanKind, SpanStatus, TraceLevel
from mirage.observe.record import OpRecord


def _make_op_record(
    op: str = "read",
    path: str = "/s3/data.csv",
    source: str = "s3",
    nbytes: int = 1024,
    timestamp: int = 1000,
    duration_ms: int = 100,
    mount_prefix: str = "/s3",
) -> OpRecord:
    return OpRecord(
        op=op,
        path=path,
        source=source,
        bytes=nbytes,
        timestamp=timestamp,
        duration_ms=duration_ms,
        mount_prefix=mount_prefix,
    )


def test_build_trace_root_span():
    buf = RingBuffer()
    collector = SpanCollector(buf)

    records = [_make_op_record()]
    root = collector.build_trace(
        command="cat /s3/data.csv",
        session_id="s1",
        agent_id="a1",
        start_time_ms=900,
        end_time_ms=1200,
        exit_code=0,
        op_records=records,
    )

    assert root.name == "execute"
    assert root.kind == SpanKind.ROOT
    assert root.level == TraceLevel.AUDIT
    assert root.status == SpanStatus.OK
    assert root.attributes["command"] == "cat /s3/data.csv"
    assert root.attributes["exit_code"] == 0
    assert root.session_id == "s1"
    assert root.agent_id == "a1"


def test_build_trace_child_spans():
    buf = RingBuffer()
    collector = SpanCollector(buf)

    records = [
        _make_op_record(op="readdir",
                        path="/s3/",
                        nbytes=0,
                        timestamp=1000,
                        duration_ms=10),
        _make_op_record(op="read",
                        path="/s3/data.csv",
                        nbytes=2048,
                        timestamp=1020,
                        duration_ms=80),
    ]
    root = collector.build_trace(
        command="ls /s3/ && cat /s3/data.csv",
        session_id="s1",
        agent_id="a1",
        start_time_ms=900,
        end_time_ms=1200,
        exit_code=0,
        op_records=records,
    )

    drained = buf.drain()
    assert len(drained) == 3

    root_spans = [s for s in drained if s.kind == SpanKind.ROOT]
    child_spans = [s for s in drained if s.kind == SpanKind.CLIENT]
    assert len(root_spans) == 1
    assert len(child_spans) == 2

    for child in child_spans:
        assert child.parent_span_id == root.span_id
        assert child.trace_id == root.trace_id
        assert child.level == TraceLevel.TRACE


def test_build_trace_error_status():
    buf = RingBuffer()
    collector = SpanCollector(buf)

    root = collector.build_trace(
        command="cat /missing",
        session_id="s1",
        agent_id="a1",
        start_time_ms=1000,
        end_time_ms=1100,
        exit_code=1,
        op_records=[],
    )
    assert root.status == SpanStatus.ERROR


def test_build_trace_metrics_aggregation():
    buf = RingBuffer()
    collector = SpanCollector(buf)

    records = [
        _make_op_record(op="read", source="s3", nbytes=1000),
        _make_op_record(op="read", source="ram", nbytes=500),
        _make_op_record(op="write", source="ram", nbytes=200),
    ]
    root = collector.build_trace(
        command="cat /s3/a | tee /data/out",
        session_id="s1",
        agent_id="a1",
        start_time_ms=1000,
        end_time_ms=1500,
        exit_code=0,
        op_records=records,
    )

    assert root.metrics.bytes_read == 1500
    assert root.metrics.bytes_written == 200
    assert root.metrics.cache_hits == 2
    assert root.metrics.cache_misses == 1
    assert root.metrics.api_calls == 1


def test_build_trace_empty_records():
    buf = RingBuffer()
    collector = SpanCollector(buf)

    root = collector.build_trace(
        command="echo hello",
        session_id="s1",
        agent_id="a1",
        start_time_ms=1000,
        end_time_ms=1050,
        exit_code=0,
        op_records=[],
    )

    drained = buf.drain()
    assert len(drained) == 1
    assert drained[0].name == "execute"


def test_child_span_attributes():
    buf = RingBuffer()
    collector = SpanCollector(buf)

    rec = _make_op_record(
        op="read",
        path="/s3/data.csv",
        source="s3",
        nbytes=4096,
        mount_prefix="/s3",
    )
    rec.fingerprint = "abc123"
    rec.revision = "v42"

    collector.build_trace(
        command="cat /s3/data.csv",
        session_id="s1",
        agent_id="a1",
        start_time_ms=900,
        end_time_ms=1200,
        exit_code=0,
        op_records=[rec],
    )

    drained = buf.drain()
    child = [s for s in drained if s.kind == SpanKind.CLIENT][0]
    assert child.attributes["op"] == "read"
    assert child.attributes["path"] == "/s3/data.csv"
    assert child.attributes["source"] == "s3"
    assert child.attributes["cache_hit"] is False
    assert child.attributes["fingerprint"] == "abc123"
    assert child.attributes["revision"] == "v42"
