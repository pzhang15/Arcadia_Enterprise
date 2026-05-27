from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import asdict
from pathlib import Path

from lineage_emitter.tracing.span import Span

logger = logging.getLogger(__name__)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS spans (
    trace_id       TEXT NOT NULL,
    span_id        TEXT PRIMARY KEY,
    parent_span_id TEXT,
    name           TEXT NOT NULL,
    kind           INTEGER NOT NULL,
    start_time_ms  INTEGER NOT NULL,
    end_time_ms    INTEGER NOT NULL,
    status         INTEGER NOT NULL,
    level          INTEGER NOT NULL,
    attributes     TEXT,
    metrics        TEXT,
    session_id     TEXT,
    agent_id       TEXT
);

CREATE INDEX IF NOT EXISTS idx_spans_trace ON spans(trace_id);
CREATE INDEX IF NOT EXISTS idx_spans_session ON spans(session_id, start_time_ms);
CREATE INDEX IF NOT EXISTS idx_spans_time ON spans(start_time_ms);

CREATE TABLE IF NOT EXISTS span_events (
    span_id      TEXT NOT NULL REFERENCES spans(span_id),
    timestamp_ms INTEGER NOT NULL,
    name         TEXT NOT NULL,
    attributes   TEXT
);

CREATE INDEX IF NOT EXISTS idx_span_events_span ON span_events(span_id);
"""


class SQLiteSpanStore:
    """SQLite-backed span storage using WAL mode for concurrent reads.

    Args:
        db_path (str): Path to the SQLite database file.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.executescript(_SCHEMA_SQL)
        self._conn.commit()

    def write_spans(self, spans: list[Span]) -> int:
        """Persist a batch of spans and their events to SQLite.

        Args:
            spans (list[Span]): Spans to write.

        Returns:
            int: Number of spans written.
        """
        if not spans:
            return 0

        span_rows = []
        event_rows = []
        for span in spans:
            span_rows.append((
                span.trace_id,
                span.span_id,
                span.parent_span_id,
                span.name,
                int(span.kind),
                span.start_time_ms,
                span.end_time_ms,
                int(span.status),
                int(span.level),
                json.dumps(span.attributes) if span.attributes else None,
                json.dumps(asdict(span.metrics)),
                span.session_id,
                span.agent_id,
            ))
            for event in span.events:
                event_rows.append((
                    span.span_id,
                    event.timestamp_ms,
                    event.name,
                    json.dumps(event.attributes) if event.attributes else None,
                ))

        cursor = self._conn.cursor()
        cursor.executemany(
            "INSERT OR REPLACE INTO spans "
            "(trace_id, span_id, parent_span_id, name, kind, start_time_ms, "
            "end_time_ms, status, level, attributes, metrics, session_id, agent_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            span_rows,
        )
        if event_rows:
            cursor.executemany(
                "INSERT INTO span_events (span_id, timestamp_ms, name, attributes) "
                "VALUES (?, ?, ?, ?)",
                event_rows,
            )
        self._conn.commit()
        return len(span_rows)

    def query_by_trace(self, trace_id: str) -> list[dict]:
        """Retrieve all spans for a given trace.

        Args:
            trace_id (str): The trace identifier.

        Returns:
            list[dict]: Span rows as dicts.
        """
        cursor = self._conn.execute(
            "SELECT * FROM spans WHERE trace_id = ? ORDER BY start_time_ms",
            (trace_id, ),
        )
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def query_by_session(
        self,
        session_id: str,
        start_ms: int | None = None,
        end_ms: int | None = None,
    ) -> list[dict]:
        """Retrieve spans for a session within an optional time range.

        Args:
            session_id (str): The session identifier.
            start_ms (int | None): Start of time range (inclusive).
            end_ms (int | None): End of time range (inclusive).

        Returns:
            list[dict]: Span rows as dicts.
        """
        query = "SELECT * FROM spans WHERE session_id = ?"
        params: list[str | int] = [session_id]
        if start_ms is not None:
            query += " AND start_time_ms >= ?"
            params.append(start_ms)
        if end_ms is not None:
            query += " AND start_time_ms <= ?"
            params.append(end_ms)
        query += " ORDER BY start_time_ms"

        cursor = self._conn.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def query_events(self, span_id: str) -> list[dict]:
        """Retrieve all events for a given span.

        Args:
            span_id (str): The span identifier.

        Returns:
            list[dict]: Event rows as dicts.
        """
        cursor = self._conn.execute(
            "SELECT * FROM span_events WHERE span_id = ? ORDER BY timestamp_ms",
            (span_id, ),
        )
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def count_spans(self, level: int | None = None) -> int:
        """Count stored spans, optionally filtered by level.

        Args:
            level (int | None): Filter by TraceLevel ordinal, or None for all.

        Returns:
            int: Number of matching spans.
        """
        if level is not None:
            cursor = self._conn.execute(
                "SELECT COUNT(*) FROM spans WHERE level = ?", (level, ))
        else:
            cursor = self._conn.execute("SELECT COUNT(*) FROM spans")
        return cursor.fetchone()[0]

    def close(self) -> None:
        self._conn.close()
