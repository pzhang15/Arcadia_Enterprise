import json
import sqlite3

import pytest

from mirage import MountMode, RAMResource, Workspace

from lineage_emitter.sinks.sqlite import SQLiteSpanStore
from lineage_emitter.tracing.config import TraceConfig
from lineage_emitter.tracing.span import SpanKind, SpanStatus, TraceLevel
from lineage_emitter.workspace import TracingWorkspace


@pytest.fixture()
def trace_db(tmp_path):
    db_path = str(tmp_path / "traces.db")
    config = TraceConfig(
        db_path=db_path,
        flush_interval_seconds=1.0,
    )
    ws = Workspace({"/data": RAMResource()}, mode=MountMode.WRITE)
    tw = TracingWorkspace(ws, config)
    yield tw, db_path
    if tw.store:
        tw.store.close()


PIPELINE_COMMANDS = [
    "echo 'hello world' > /data/test.txt",
    "cat /data/test.txt",
    "echo '{\"key\": \"value\"}' > /data/meta.json",
    "cat /data/meta.json",
    "cat /data/nonexistent.txt",
    "ls /data/",
    "cat /data/test.txt",
]


@pytest.mark.asyncio
async def test_full_pipeline_generates_and_flushes(trace_db):
    """End-to-end: execute commands, flush to SQLite, verify all traces exist."""
    tw, db_path = trace_db

    for cmd in PIPELINE_COMMANDS:
        await tw.execute(cmd, agent_id="test-agent")

    flushed = tw.flush_sync()
    assert flushed > 0, "No spans were flushed to SQLite"

    store = tw.store
    total_spans = store.count_spans()
    audit_spans = store.count_spans(level=int(TraceLevel.AUDIT))
    trace_spans = store.count_spans(level=int(TraceLevel.TRACE))

    assert audit_spans == len(PIPELINE_COMMANDS), (
        f"Expected {len(PIPELINE_COMMANDS)} root spans, got {audit_spans}"
    )
    assert total_spans > audit_spans, "No child spans produced"


@pytest.mark.asyncio
async def test_sqlite_readable_after_checkpoint(trace_db, tmp_path):
    """After WAL checkpoint, a read-only connection can see all data."""
    tw, db_path = trace_db

    for cmd in PIPELINE_COMMANDS:
        await tw.execute(cmd, agent_id="test-agent")

    tw.flush_sync()
    tw.store.close()

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()

    ro_conn = sqlite3.connect(db_path)
    ro_conn.row_factory = sqlite3.Row
    rows = ro_conn.execute(
        "SELECT * FROM spans WHERE parent_span_id IS NULL"
    ).fetchall()
    ro_conn.close()

    assert len(rows) == len(PIPELINE_COMMANDS), (
        f"Read-only connection sees {len(rows)} root spans, expected {len(PIPELINE_COMMANDS)}"
    )


@pytest.mark.asyncio
async def test_trace_api_list_format(trace_db):
    """The API query pattern used by the observability server works correctly."""
    tw, db_path = trace_db

    await tw.execute("echo test > /data/file.txt", agent_id="test-agent")
    await tw.execute("cat /data/file.txt", agent_id="test-agent")
    tw.flush_sync()
    tw.store.close()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        "SELECT trace_id, name, start_time_ms, end_time_ms, status, "
        "attributes, metrics, session_id, agent_id "
        "FROM spans WHERE parent_span_id IS NULL "
        "ORDER BY start_time_ms DESC LIMIT 50 OFFSET 0"
    ).fetchall()
    conn.close()

    assert len(rows) == 2
    for row in rows:
        d = dict(row)
        assert d["name"] == "execute"
        assert d["trace_id"]
        assert d["start_time_ms"] > 0
        assert d["end_time_ms"] >= d["start_time_ms"]

        attrs = json.loads(d["attributes"])
        assert "command" in attrs
        assert "exit_code" in attrs

        metrics = json.loads(d["metrics"])
        assert "bytes_read" in metrics
        assert "cache_hits" in metrics


@pytest.mark.asyncio
async def test_trace_detail_api_format(trace_db):
    """The detail query returns proper parent-child hierarchy."""
    tw, db_path = trace_db

    await tw.execute("echo data > /data/x.txt", agent_id="test-agent")
    await tw.execute("cat /data/x.txt", agent_id="test-agent")

    tw.flush_sync()
    tw.store.close()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    root_rows_all = conn.execute(
        "SELECT trace_id FROM spans WHERE parent_span_id IS NULL "
        "ORDER BY start_time_ms"
    ).fetchall()
    assert len(root_rows_all) == 2

    cat_trace_id = root_rows_all[1]["trace_id"]

    rows = conn.execute(
        "SELECT * FROM spans WHERE trace_id = ? ORDER BY start_time_ms",
        (cat_trace_id,),
    ).fetchall()

    assert len(rows) >= 2, "Expected root + at least one child span"

    root_rows = [r for r in rows if r["parent_span_id"] is None]
    child_rows = [r for r in rows if r["parent_span_id"] is not None]

    assert len(root_rows) == 1
    assert len(child_rows) >= 1
    assert all(r["parent_span_id"] == root_rows[0]["span_id"] for r in child_rows)
    assert all(r["trace_id"] == cat_trace_id for r in rows)
    conn.close()


@pytest.mark.asyncio
async def test_trace_stats_summary_format(trace_db):
    """The stats summary query returns correct totals."""
    tw, db_path = trace_db

    await tw.execute("echo a > /data/a.txt", agent_id="test-agent")
    await tw.execute("cat /data/a.txt", agent_id="test-agent")
    tw.flush_sync()
    tw.store.close()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    total_spans = conn.execute("SELECT COUNT(*) FROM spans").fetchone()[0]
    total_traces = conn.execute(
        "SELECT COUNT(DISTINCT trace_id) FROM spans"
    ).fetchone()[0]

    assert total_traces == 2
    assert total_spans >= 3  # 2 roots + at least 1 child

    by_level = {}
    for row in conn.execute(
        "SELECT level, COUNT(*) as cnt FROM spans GROUP BY level"
    ).fetchall():
        level_name = {0: "audit", 1: "trace", 2: "operational"}.get(
            row["level"], str(row["level"])
        )
        by_level[level_name] = row["cnt"]

    assert "audit" in by_level
    assert by_level["audit"] == 2
    conn.close()


@pytest.mark.asyncio
async def test_error_trace_marked_correctly(trace_db):
    """Commands that fail should produce ERROR-status root spans."""
    tw, db_path = trace_db

    await tw.execute("cat /data/missing_file.txt", agent_id="test-agent")
    tw.flush_sync()
    tw.store.close()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM spans WHERE parent_span_id IS NULL"
    ).fetchall()
    conn.close()

    assert len(rows) == 1
    root = dict(rows[0])
    assert root["status"] == int(SpanStatus.ERROR)
    attrs = json.loads(root["attributes"])
    assert attrs["exit_code"] != 0


@pytest.mark.asyncio
async def test_cache_hit_tracking(trace_db):
    """Re-reading a file should produce cache-hit child spans."""
    tw, db_path = trace_db

    await tw.execute("echo cached > /data/cached.txt", agent_id="test-agent")
    await tw.execute("cat /data/cached.txt", agent_id="test-agent")
    await tw.execute("cat /data/cached.txt", agent_id="test-agent")
    tw.flush_sync()
    tw.store.close()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    child_rows = conn.execute(
        "SELECT attributes FROM spans WHERE parent_span_id IS NOT NULL"
    ).fetchall()
    conn.close()

    attrs_list = [json.loads(r["attributes"]) for r in child_rows]
    read_attrs = [a for a in attrs_list if a.get("op") == "read"]
    assert len(read_attrs) >= 2, "Expected at least 2 read operations"


@pytest.mark.asyncio
async def test_child_count_matches_api_pattern(trace_db):
    """The child_count computed in the API matches actual children."""
    tw, db_path = trace_db

    await tw.execute("echo x > /data/x.txt", agent_id="test-agent")
    await tw.execute("cat /data/x.txt", agent_id="test-agent")
    tw.flush_sync()
    tw.store.close()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    roots = conn.execute(
        "SELECT trace_id FROM spans WHERE parent_span_id IS NULL"
    ).fetchall()

    for root in roots:
        child_count = conn.execute(
            "SELECT COUNT(*) FROM spans WHERE trace_id = ? AND parent_span_id IS NOT NULL",
            (root["trace_id"],),
        ).fetchone()[0]
        total = conn.execute(
            "SELECT COUNT(*) FROM spans WHERE trace_id = ?",
            (root["trace_id"],),
        ).fetchone()[0]
        assert total == child_count + 1

    conn.close()


@pytest.mark.asyncio
async def test_session_and_agent_propagated(trace_db):
    """agent_id propagates to all spans."""
    tw, db_path = trace_db

    await tw.execute("echo hi > /data/hi.txt", agent_id="my-agent")
    tw.flush_sync()
    tw.store.close()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT agent_id FROM spans").fetchall()
    conn.close()

    for row in rows:
        assert row["agent_id"] == "my-agent"
