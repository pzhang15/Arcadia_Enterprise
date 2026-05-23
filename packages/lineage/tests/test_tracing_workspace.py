import pytest

from mirage import MountMode, RAMResource, Workspace

from lineage_emitter.tracing.config import TraceConfig
from lineage_emitter.tracing.span import SpanKind, SpanStatus, TraceLevel
from lineage_emitter.workspace import TracingWorkspace


@pytest.fixture()
def tracing_ws(tmp_path):
    ws = Workspace({"/data": RAMResource()}, mode=MountMode.WRITE)
    config = TraceConfig(db_path=str(tmp_path / "traces.db"))
    tw = TracingWorkspace(ws, config)
    yield tw
    if tw.store:
        tw.store.close()


@pytest.fixture()
def tracing_ws_no_db():
    ws = Workspace({"/data": RAMResource()}, mode=MountMode.WRITE)
    tw = TracingWorkspace(ws)
    yield tw


@pytest.mark.asyncio
async def test_execute_delegates(tracing_ws):
    result = await tracing_ws.execute("echo hello > /data/test.txt")
    assert result.exit_code == 0


@pytest.mark.asyncio
async def test_execute_produces_spans(tracing_ws):
    await tracing_ws.execute("echo hello > /data/test.txt")
    await tracing_ws.execute("cat /data/test.txt")

    spans = tracing_ws.buffer.drain()
    assert len(spans) > 0

    root_spans = [s for s in spans if s.kind == SpanKind.ROOT]
    assert len(root_spans) == 2


@pytest.mark.asyncio
async def test_root_span_has_command(tracing_ws):
    await tracing_ws.execute("echo test > /data/x.txt")
    spans = tracing_ws.buffer.drain()
    root = [s for s in spans if s.kind == SpanKind.ROOT][0]
    assert root.attributes["command"] == "echo test > /data/x.txt"


@pytest.mark.asyncio
async def test_child_spans_from_read(tracing_ws):
    await tracing_ws.execute("echo data > /data/file.txt")
    tracing_ws.buffer.drain()

    await tracing_ws.execute("cat /data/file.txt")
    spans = tracing_ws.buffer.drain()

    child_spans = [s for s in spans if s.kind == SpanKind.CLIENT]
    assert len(child_spans) > 0
    assert any(s.attributes.get("op") == "read" for s in child_spans)


@pytest.mark.asyncio
async def test_error_exit_code(tracing_ws):
    await tracing_ws.execute("cat /data/nonexistent")
    spans = tracing_ws.buffer.drain()
    root = [s for s in spans if s.kind == SpanKind.ROOT][0]
    assert root.status == SpanStatus.ERROR
    assert root.attributes["exit_code"] != 0


@pytest.mark.asyncio
async def test_flush_to_sqlite(tracing_ws):
    await tracing_ws.execute("echo hello > /data/test.txt")
    flushed = tracing_ws.flush_sync()
    assert flushed > 0

    rows = tracing_ws.store.query_by_session("default")
    assert len(rows) > 0


@pytest.mark.asyncio
async def test_no_db_still_traces(tracing_ws_no_db):
    await tracing_ws_no_db.execute("echo hello")
    spans = tracing_ws_no_db.buffer.drain()
    assert len(spans) > 0


@pytest.mark.asyncio
async def test_multiple_executes_independent_traces(tracing_ws):
    await tracing_ws.execute("echo a > /data/a.txt")
    await tracing_ws.execute("echo b > /data/b.txt")

    spans = tracing_ws.buffer.drain()
    root_spans = [s for s in spans if s.kind == SpanKind.ROOT]
    assert len(root_spans) == 2

    trace_ids = {s.trace_id for s in root_spans}
    assert len(trace_ids) == 2


@pytest.mark.asyncio
async def test_span_parent_child_linkage(tracing_ws):
    await tracing_ws.execute("echo x > /data/x.txt")
    tracing_ws.buffer.drain()

    await tracing_ws.execute("cat /data/x.txt")
    spans = tracing_ws.buffer.drain()

    root = [s for s in spans if s.kind == SpanKind.ROOT][0]
    children = [s for s in spans if s.parent_span_id == root.span_id]
    assert len(children) > 0
    assert all(s.trace_id == root.trace_id for s in children)
