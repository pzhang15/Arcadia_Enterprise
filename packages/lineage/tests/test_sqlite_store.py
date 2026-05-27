import pytest
from lineage_emitter.sinks.sqlite import SQLiteSpanStore
from lineage_emitter.tracing.span import (Span, SpanEvent, SpanKind,
                                          SpanMetrics, SpanStatus, TraceLevel)


@pytest.fixture()
def store(tmp_path):
    db_path = str(tmp_path / "test_traces.db")
    s = SQLiteSpanStore(db_path)
    yield s
    s.close()


def _make_span(
    trace_id: str = "trace1",
    name: str = "read",
    start: int = 1000,
    end: int = 1100,
    session_id: str = "sess1",
    level: TraceLevel = TraceLevel.TRACE,
) -> Span:
    return Span(
        trace_id=trace_id,
        name=name,
        kind=SpanKind.CLIENT,
        start_time_ms=start,
        end_time_ms=end,
        status=SpanStatus.OK,
        level=level,
        session_id=session_id,
        agent_id="agent1",
        metrics=SpanMetrics(bytes_read=1024),
    )


def test_write_and_query_by_trace(store):
    spans = [
        _make_span(name="execute", start=1000, end=1200),
        _make_span(name="read", start=1050, end=1100),
    ]
    written = store.write_spans(spans)
    assert written == 2

    rows = store.query_by_trace("trace1")
    assert len(rows) == 2
    assert rows[0]["name"] == "execute"
    assert rows[1]["name"] == "read"


def test_query_by_session(store):
    store.write_spans([
        _make_span(session_id="s1", start=1000),
        _make_span(session_id="s1", start=2000),
        _make_span(session_id="s2", start=1500),
    ])

    rows = store.query_by_session("s1")
    assert len(rows) == 2

    rows = store.query_by_session("s1", start_ms=1500)
    assert len(rows) == 1
    assert rows[0]["start_time_ms"] == 2000


def test_query_by_session_time_range(store):
    store.write_spans([
        _make_span(session_id="s1", start=1000),
        _make_span(session_id="s1", start=2000),
        _make_span(session_id="s1", start=3000),
    ])
    rows = store.query_by_session("s1", start_ms=1500, end_ms=2500)
    assert len(rows) == 1
    assert rows[0]["start_time_ms"] == 2000


def test_write_empty_list(store):
    assert store.write_spans([]) == 0


def test_span_events_persisted(store):
    span = _make_span()
    span.events.append(
        SpanEvent(
            timestamp_ms=1050,
            name="cache_miss",
            attributes={"path": "/data/file.txt"},
        ))
    store.write_spans([span])

    events = store.query_events(span.span_id)
    assert len(events) == 1
    assert events[0]["name"] == "cache_miss"


def test_count_spans(store):
    store.write_spans([
        _make_span(level=TraceLevel.AUDIT),
        _make_span(level=TraceLevel.TRACE),
        _make_span(level=TraceLevel.TRACE),
    ])
    assert store.count_spans() == 3
    assert store.count_spans(level=int(TraceLevel.AUDIT)) == 1
    assert store.count_spans(level=int(TraceLevel.TRACE)) == 2


def test_idempotent_write(store):
    span = _make_span()
    store.write_spans([span])
    store.write_spans([span])
    assert store.count_spans() == 1
