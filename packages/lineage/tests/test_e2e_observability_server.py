import json
import sqlite3

import pytest

from mirage import MountMode, RAMResource, Workspace

from lineage_emitter.tracing.config import TraceConfig
from lineage_emitter.tracing.span import SpanKind, SpanStatus, TraceLevel
from lineage_emitter.workspace import TracingWorkspace


@pytest.fixture()
def populated_db(tmp_path):
    """Create a fully populated traces DB simulating the docker trace-generator."""
    db_path = str(tmp_path / "traces.db")
    config = TraceConfig(db_path=db_path, flush_interval_seconds=1.0)
    ws = Workspace({"/data": RAMResource()}, mode=MountMode.WRITE)
    tw = TracingWorkspace(ws, config)

    commands = [
        "echo 'incident report' > /data/incident.txt",
        "echo '{\"severity\": \"high\"}' > /data/meta.json",
        "cat /data/incident.txt",
        "cat /data/meta.json",
        "cat /data/nonexistent.txt",
        "ls /data/",
        "cat /data/incident.txt",
    ]

    import asyncio
    loop = asyncio.new_event_loop()
    for cmd in commands:
        loop.run_until_complete(tw.execute(cmd, agent_id="test-agent"))
    loop.close()

    tw.flush_sync()
    if tw.store:
        tw.store.close()

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()

    yield db_path


def _query_traces_list(db_path: str, limit: int = 50, offset: int = 0) -> list[dict]:
    """Replicate the /api/traces endpoint logic."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT trace_id, name, start_time_ms, end_time_ms, status, "
        "attributes, metrics, session_id, agent_id "
        "FROM spans WHERE parent_span_id IS NULL "
        "ORDER BY start_time_ms DESC LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()
    traces = []
    for row in rows:
        d = dict(row)
        child_count = conn.execute(
            "SELECT COUNT(*) FROM spans WHERE trace_id = ? AND parent_span_id IS NOT NULL",
            (d["trace_id"],),
        ).fetchone()[0]
        d["child_count"] = child_count
        if d.get("attributes"):
            d["attributes"] = json.loads(d["attributes"])
        if d.get("metrics"):
            d["metrics"] = json.loads(d["metrics"])
        traces.append(d)
    conn.close()
    return traces


def _query_trace_detail(db_path: str, trace_id: str) -> dict:
    """Replicate the /api/traces/{trace_id} endpoint logic."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM spans WHERE trace_id = ? ORDER BY start_time_ms",
        (trace_id,),
    ).fetchall()
    spans = []
    for row in rows:
        d = dict(row)
        if d.get("attributes"):
            d["attributes"] = json.loads(d["attributes"])
        if d.get("metrics"):
            d["metrics"] = json.loads(d["metrics"])
        events = conn.execute(
            "SELECT * FROM span_events WHERE span_id = ? ORDER BY timestamp_ms",
            (d["span_id"],),
        ).fetchall()
        d["events"] = [dict(e) for e in events]
        for e in d["events"]:
            if e.get("attributes"):
                e["attributes"] = json.loads(e["attributes"])
        spans.append(d)
    conn.close()
    return {"trace_id": trace_id, "spans": spans}


def _query_stats(db_path: str) -> dict:
    """Replicate the /api/traces/stats/summary endpoint logic."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    total_spans = conn.execute("SELECT COUNT(*) FROM spans").fetchone()[0]
    total_traces = conn.execute(
        "SELECT COUNT(DISTINCT trace_id) FROM spans"
    ).fetchone()[0]
    by_level = {}
    for row in conn.execute(
        "SELECT level, COUNT(*) as cnt FROM spans GROUP BY level"
    ).fetchall():
        level_name = {0: "audit", 1: "trace", 2: "operational"}.get(
            row["level"], str(row["level"])
        )
        by_level[level_name] = row["cnt"]
    conn.close()
    return {
        "total_traces": total_traces,
        "total_spans": total_spans,
        "by_level": by_level,
    }


class TestTraceListEndpoint:
    def test_returns_all_traces(self, populated_db):
        traces = _query_traces_list(populated_db)
        assert len(traces) == 7

    def test_trace_fields_present(self, populated_db):
        traces = _query_traces_list(populated_db)
        for t in traces:
            assert "trace_id" in t
            assert "name" in t
            assert "start_time_ms" in t
            assert "end_time_ms" in t
            assert "status" in t
            assert "attributes" in t
            assert "metrics" in t
            assert "child_count" in t

    def test_trace_has_command_attribute(self, populated_db):
        traces = _query_traces_list(populated_db)
        for t in traces:
            assert "command" in t["attributes"], (
                f"Trace missing 'command' in attributes: {t['attributes']}"
            )

    def test_trace_metrics_structure(self, populated_db):
        traces = _query_traces_list(populated_db)
        for t in traces:
            m = t["metrics"]
            assert "bytes_read" in m
            assert "bytes_written" in m
            assert "cache_hits" in m
            assert "cache_misses" in m
            assert "api_calls" in m

    def test_error_trace_present(self, populated_db):
        traces = _query_traces_list(populated_db)
        error_traces = [t for t in traces if t["status"] == 1]
        assert len(error_traces) >= 1, "No error traces found"

    def test_pagination(self, populated_db):
        page1 = _query_traces_list(populated_db, limit=3, offset=0)
        page2 = _query_traces_list(populated_db, limit=3, offset=3)
        assert len(page1) == 3
        assert len(page2) >= 1
        ids1 = {t["trace_id"] for t in page1}
        ids2 = {t["trace_id"] for t in page2}
        assert ids1.isdisjoint(ids2), "Pages overlap"


class TestTraceDetailEndpoint:
    def test_detail_returns_spans(self, populated_db):
        traces = _query_traces_list(populated_db)
        for t in traces[:3]:
            detail = _query_trace_detail(populated_db, t["trace_id"])
            assert len(detail["spans"]) >= 1
            assert detail["trace_id"] == t["trace_id"]

    def test_detail_has_root_and_children(self, populated_db):
        traces = _query_traces_list(populated_db)
        write_traces = [
            t for t in traces if "echo" in t["attributes"].get("command", "")
        ]
        assert len(write_traces) >= 1

        detail = _query_trace_detail(populated_db, write_traces[0]["trace_id"])
        roots = [s for s in detail["spans"] if s["parent_span_id"] is None]
        children = [s for s in detail["spans"] if s["parent_span_id"] is not None]
        assert len(roots) == 1
        assert len(children) >= 1

    def test_detail_span_fields(self, populated_db):
        traces = _query_traces_list(populated_db)
        detail = _query_trace_detail(populated_db, traces[0]["trace_id"])
        for span in detail["spans"]:
            assert "trace_id" in span
            assert "span_id" in span
            assert "name" in span
            assert "kind" in span
            assert "start_time_ms" in span
            assert "end_time_ms" in span
            assert "status" in span
            assert "level" in span
            assert "metrics" in span

    def test_nonexistent_trace(self, populated_db):
        detail = _query_trace_detail(populated_db, "nonexistent-trace-id")
        assert len(detail["spans"]) == 0


class TestStatsEndpoint:
    def test_stats_totals(self, populated_db):
        stats = _query_stats(populated_db)
        assert stats["total_traces"] == 7
        assert stats["total_spans"] > 7

    def test_stats_by_level(self, populated_db):
        stats = _query_stats(populated_db)
        assert "audit" in stats["by_level"]
        assert stats["by_level"]["audit"] == 7
        if "trace" in stats["by_level"]:
            assert stats["by_level"]["trace"] > 0


class TestReadOnlyAccess:
    def test_readonly_connection_works(self, populated_db):
        """query_only pragma should allow reads."""
        conn = sqlite3.connect(populated_db)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only = ON")
        count = conn.execute("SELECT COUNT(*) FROM spans").fetchone()[0]
        assert count > 0
        conn.close()

    def test_readonly_cannot_write(self, populated_db):
        """query_only pragma should reject writes."""
        conn = sqlite3.connect(populated_db)
        conn.execute("PRAGMA query_only = ON")
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("DELETE FROM spans")
        conn.close()
