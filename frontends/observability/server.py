import asyncio
import json
import os
import sqlite3
import time
from collections import deque
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

RESULTS_DIR = Path(
    os.environ.get(
        "RESULTS_DIR",
        str(Path(__file__).resolve().parent.parent / "results"),
    ))

TRACES_DB = os.environ.get("TRACES_DB", "")

app = FastAPI(title="Mirage Observability Relay")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_event_buffer: deque[dict] = deque(maxlen=5000)
_subscribers: list[asyncio.Queue[dict]] = []


async def _broadcast(event: dict) -> None:
    dead: list[asyncio.Queue[dict]] = []
    for q in _subscribers:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        _subscribers.remove(q)


@app.post("/ingest")
async def ingest(request: Request) -> dict:
    body = await request.json()
    events = body if isinstance(body, list) else [body]
    for evt in events:
        if "timestamp" not in evt:
            evt["timestamp"] = int(time.time() * 1000)
        _event_buffer.append(evt)
        await _broadcast(evt)
    return {"accepted": len(events)}


async def _event_generator(
    queue: asyncio.Queue[dict],
    after: int,
) -> None:
    for evt in _event_buffer:
        ts = evt.get("timestamp", 0)
        if ts > after:
            yield f"data: {json.dumps(evt)}\n\n"

    while True:
        try:
            evt = await asyncio.wait_for(queue.get(), timeout=30.0)
            yield f"data: {json.dumps(evt)}\n\n"
        except asyncio.TimeoutError:
            yield ": keepalive\n\n"


@app.get("/events")
async def events(request: Request, after: int = 0) -> StreamingResponse:
    queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=500)
    _subscribers.append(queue)

    async def cleanup_generator():
        try:
            async for chunk in _event_generator(queue, after):
                yield chunk
        finally:
            if queue in _subscribers:
                _subscribers.remove(queue)

    return StreamingResponse(
        cleanup_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/results")
async def list_results() -> list[dict]:
    sweeps: list[dict] = []
    if not RESULTS_DIR.exists():
        return sweeps
    for scenario_dir in sorted(RESULTS_DIR.iterdir()):
        if not scenario_dir.is_dir():
            continue
        for sweep_dir in sorted(scenario_dir.iterdir()):
            if not sweep_dir.is_dir():
                continue
            agg = sweep_dir / "aggregate.json"
            if agg.exists() or (sweep_dir / "runs").exists():
                sweeps.append({
                    "scenario": scenario_dir.name,
                    "sweep_id": sweep_dir.name,
                    "path": str(sweep_dir),
                })
    return sweeps


@app.get("/api/results/{scenario}/{sweep_id}")
async def get_aggregate(scenario: str, sweep_id: str) -> dict:
    agg_path = RESULTS_DIR / scenario / sweep_id / "aggregate.json"
    if agg_path.exists():
        return json.loads(agg_path.read_text())
    runs_dir = RESULTS_DIR / scenario / sweep_id / "runs"
    if not runs_dir.exists():
        return {"error": "not found", "n_runs": 0}
    cards = []
    for run_dir in sorted(runs_dir.iterdir()):
        sc = run_dir / "scorecard.json"
        if sc.exists():
            cards.append(json.loads(sc.read_text()))
    return {"runs": cards, "n_runs": len(cards)}


@app.get("/api/results/{scenario}/{sweep_id}/runs/{run_id}")
async def get_run(scenario: str, sweep_id: str, run_id: str) -> dict:
    run_dir = RESULTS_DIR / scenario / sweep_id / "runs" / run_id
    sc = run_dir / "scorecard.json"
    if sc.exists():
        return json.loads(sc.read_text())
    return {"error": "not found"}


def _get_traces_db() -> sqlite3.Connection | None:
    db_path = TRACES_DB
    if not db_path or not Path(db_path).exists():
        return None
    try:
        conn = sqlite3.connect(f"file:{db_path}?immutable=1", uri=True)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.OperationalError:
        return None


@app.get("/api/traces")
async def list_traces(limit: int = 50, offset: int = 0) -> list[dict]:
    conn = _get_traces_db()
    if conn is None:
        return []
    try:
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
                (d["trace_id"], ),
            ).fetchone()[0]
            d["child_count"] = child_count
            if d.get("attributes"):
                d["attributes"] = json.loads(d["attributes"])
            if d.get("metrics"):
                d["metrics"] = json.loads(d["metrics"])
            traces.append(d)
        return traces
    finally:
        conn.close()


@app.get("/api/traces/{trace_id}")
async def get_trace(trace_id: str) -> dict:
    conn = _get_traces_db()
    if conn is None:
        return {"error": "no trace database configured"}
    try:
        rows = conn.execute(
            "SELECT * FROM spans WHERE trace_id = ? ORDER BY start_time_ms",
            (trace_id, ),
        ).fetchall()
        if not rows:
            return {"error": "trace not found", "spans": []}
        spans = []
        for row in rows:
            d = dict(row)
            if d.get("attributes"):
                d["attributes"] = json.loads(d["attributes"])
            if d.get("metrics"):
                d["metrics"] = json.loads(d["metrics"])
            events = conn.execute(
                "SELECT * FROM span_events WHERE span_id = ? ORDER BY timestamp_ms",
                (d["span_id"], ),
            ).fetchall()
            d["events"] = [dict(e) for e in events]
            for e in d["events"]:
                if e.get("attributes"):
                    e["attributes"] = json.loads(e["attributes"])
            spans.append(d)
        return {"trace_id": trace_id, "spans": spans}
    finally:
        conn.close()


@app.get("/api/traces/stats/summary")
async def trace_stats() -> dict:
    conn = _get_traces_db()
    if conn is None:
        return {"total_traces": 0, "total_spans": 0}
    try:
        total_spans = conn.execute("SELECT COUNT(*) FROM spans").fetchone()[0]
        total_traces = conn.execute(
            "SELECT COUNT(DISTINCT trace_id) FROM spans").fetchone()[0]
        by_level = {}
        for row in conn.execute(
                "SELECT level, COUNT(*) as cnt FROM spans GROUP BY level"
        ).fetchall():
            level_name = {
                0: "audit",
                1: "trace",
                2: "operational"
            }.get(row["level"], str(row["level"]))
            by_level[level_name] = row["cnt"]
        return {
            "total_traces": total_traces,
            "total_spans": total_spans,
            "by_level": by_level,
        }
    finally:
        conn.close()


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "events_buffered": len(_event_buffer),
        "subscribers": len(_subscribers),
        "traces_db": TRACES_DB or None,
    }


dist_dir = Path(__file__).parent / "dist"
if dist_dir.exists():
    app.mount("/",
              StaticFiles(directory=str(dist_dir), html=True),
              name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8082)
