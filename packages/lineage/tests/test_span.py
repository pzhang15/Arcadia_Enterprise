from lineage_emitter.tracing.span import (Span, SpanKind, SpanMetrics,
                                          SpanStatus, TraceLevel)


def test_span_defaults():
    span = Span(trace_id="abc123")
    assert span.trace_id == "abc123"
    assert span.span_id
    assert span.parent_span_id is None
    assert span.kind == SpanKind.INTERNAL
    assert span.status == SpanStatus.OK
    assert span.end_time_ms == 0
    assert span.level == TraceLevel.TRACE
    assert span.metrics.bytes_read == 0


def test_span_finish():
    span = Span(trace_id="t1", start_time_ms=1000)
    assert span.duration_ms == 0
    span.finish()
    assert span.end_time_ms > 0
    assert span.status == SpanStatus.OK


def test_span_finish_with_error():
    span = Span(trace_id="t1")
    span.finish(status=SpanStatus.ERROR)
    assert span.status == SpanStatus.ERROR


def test_span_duration():
    span = Span(trace_id="t1", start_time_ms=1000, end_time_ms=1500)
    assert span.duration_ms == 500


def test_span_add_event():
    span = Span(trace_id="t1")
    span.add_event("cache_miss", {"path": "/data/file.txt"})
    assert len(span.events) == 1
    assert span.events[0].name == "cache_miss"
    assert span.events[0].attributes["path"] == "/data/file.txt"


def test_trace_level_ordering():
    assert TraceLevel.AUDIT < TraceLevel.TRACE < TraceLevel.OPERATIONAL


def test_span_metrics():
    m = SpanMetrics(bytes_read=1024, cache_hits=3, cache_misses=1, api_calls=1)
    assert m.bytes_read == 1024
    assert m.cache_hits == 3


def test_span_kind_values():
    assert SpanKind.ROOT == 0
    assert SpanKind.INTERNAL == 1
    assert SpanKind.CLIENT == 2
