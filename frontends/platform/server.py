import asyncio
import json
import logging
import os
import sqlite3
import sys
import tempfile
import time
import uuid
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_MIRAGE_PYTHON = _REPO_ROOT / "vendor" / "mirage" / "python"
_EVAL_ROOT = _REPO_ROOT / "packages" / "eval"
_STORE_ROOT = _REPO_ROOT / "packages" / "store"
for _bootstrap_path in (_MIRAGE_PYTHON, _EVAL_ROOT, _STORE_ROOT):
    _boot = str(_bootstrap_path)
    if _boot not in sys.path:
        sys.path.insert(0, _boot)

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

try:
    from dotenv import load_dotenv

    _ENV_FILE = _REPO_ROOT / ".env"
    if _ENV_FILE.exists():
        load_dotenv(_ENV_FILE, override=False)
except ImportError:
    pass

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

try:
    from scenarios.northhill_corp.mounts import build_l1_workspace
    from scenarios.northhill_corp.seed import main as _seed_northhill
except ImportError:
    build_l1_workspace = None
    _seed_northhill = None

try:
    from mirage import MountMode, RAMResource, Workspace
    from mirage.resource.disk import DiskResource

    _HAS_MIRAGE = True
except ImportError:
    _HAS_MIRAGE = False

try:
    from arcadia_store import (AsyncFlusher, RingEventBuffer, StoreConfig,
                               StreamCoalescer, build_store, run_migrations)
    from arcadia_store.types import MessageRow, SessionRow, StreamEventRow

    _HAS_STORE = True
except Exception:
    _HAS_STORE = False

logger = logging.getLogger(__name__)
DISK_ROOT = Path(
    os.environ.get(
        "DISK_ROOT",
        str(_REPO_ROOT / "packages" / "eval" / "scenarios" / "northhill_corp" /
            "fixture" / "disk"),
    ))
RESULTS_DIR = Path(
    os.environ.get(
        "RESULTS_DIR",
        str(_REPO_ROOT / "packages" / "eval" / "results"),
    ))
TRACES_DB = os.environ.get("TRACES_DB", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL",
                                 "https://api.openai.com/v1")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"sqlite+aiosqlite:///{_REPO_ROOT / '.arcadia' / 'arcadia.db'}",
)
OPENAI_REASONING = os.environ.get("OPENAI_REASONING",
                                  "1").lower() not in ("0", "false", "no", "")
STREAM_EVENT_RETENTION_MAX = int(
    os.environ.get("STREAM_EVENT_RETENTION_MAX", "200000"))
STORE_FLUSH_INTERVAL = float(os.environ.get("STORE_FLUSH_INTERVAL", "2.0"))
CONSOLE_SNAP_DIR = os.environ.get("CONSOLE_SNAP_DIR", "")
STORE_CONNECT_ATTEMPTS = int(os.environ.get("STORE_CONNECT_ATTEMPTS", "5"))
STORE_CONNECT_DELAY = float(os.environ.get("STORE_CONNECT_DELAY", "1.0"))


def _disk_has_fixture_data() -> bool:
    if not DISK_ROOT.exists():
        return False
    return any(p.is_dir() and not p.name.startswith(".")
               for p in DISK_ROOT.iterdir())


def _ensure_fixture_disk() -> None:
    if _disk_has_fixture_data():
        return
    if _seed_northhill is None:
        logger.warning(
            "Fixture disk missing at %s and seed module unavailable",
            DISK_ROOT,
        )
        return
    logger.info("Seeding northhill_corp fixture data at %s", DISK_ROOT)
    DISK_ROOT.parent.mkdir(parents=True, exist_ok=True)
    _seed_northhill(DISK_ROOT, clean=True)


def _ensure_sqlite_dir(dsn: str) -> None:
    marker = "sqlite+aiosqlite:///"
    if not dsn.startswith(marker):
        return
    path = dsn[len(marker):]
    if not path or path == ":memory:":
        return
    Path(path).parent.mkdir(parents=True, exist_ok=True)


async def _setup_persistence() -> None:
    """Connect the store and start the flusher, degrading gracefully on failure.

    A persistence outage (unreachable database, missing driver) must never take
    the whole platform down: on failure we log loudly and leave the store unset,
    so every endpoint falls back to its in-memory path.
    """
    global _store, _flusher, _persist_buffer, _stream_seq, _retention_task
    if not _HAS_STORE:
        logger.warning(
            "arcadia_store is not importable — running in-memory only. "
            "Rebuild the image (docker compose build) to enable persistence.")
        return
    cfg = StoreConfig(dsn=DATABASE_URL,
                      flush_interval_seconds=STORE_FLUSH_INTERVAL,
                      stream_retention_max=STREAM_EVENT_RETENTION_MAX)
    last_err: Exception | None = None
    for attempt in range(1, STORE_CONNECT_ATTEMPTS + 1):
        try:
            _ensure_sqlite_dir(DATABASE_URL)
            await run_migrations(DATABASE_URL)
            store = build_store(cfg)
            await store.init()
            _store = store
            _persist_buffer = RingEventBuffer(cfg)
            _flusher = AsyncFlusher(_persist_buffer, _store, cfg)
            _flusher.start()
            _stream_seq = await _store.max_stream_seq()
            await _hydrate_relay_tail()
            await _rehydrate_console_workspaces()
            _retention_task = asyncio.ensure_future(_retention_loop())
            logger.info("Persistence ready (db=%s)", _store.dialect)
            return
        except Exception as exc:
            last_err = exc
            if attempt < STORE_CONNECT_ATTEMPTS:
                await asyncio.sleep(STORE_CONNECT_DELAY)
    _store = None
    _flusher = None
    _persist_buffer = None
    logger.warning(
        "Persistence unavailable after %d attempts (%s) — running in-memory "
        "only. Set DATABASE_URL to a reachable database to enable persistence.",
        STORE_CONNECT_ATTEMPTS, last_err)


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    _ensure_fixture_disk()
    await _setup_persistence()
    probe = _build_workspace([])
    logger.info(
        "Platform runtime ready: mirage=%s eval=%s disk=%s workspace=%s "
        "persistence=%s",
        _HAS_MIRAGE,
        build_l1_workspace is not None,
        _disk_has_fixture_data(),
        probe is not None,
        _store.dialect if _store is not None else "off",
    )
    try:
        yield
    finally:
        if _retention_task is not None:
            _retention_task.cancel()
        if _flusher is not None:
            await _flusher.stop()
        if _store is not None:
            await _store.close()


app = FastAPI(title="Arcadia Platform", lifespan=_lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── SSE Event Relay ────────────────────────────────────────────────────

_event_buffer: deque[dict] = deque(maxlen=5000)
_subscribers: list[asyncio.Queue[dict]] = []
_store = None
_flusher = None
_persist_buffer = None
_stream_seq = 0
_retention_task = None


async def _broadcast(event: dict) -> None:
    dead: list[asyncio.Queue[dict]] = []
    for q in _subscribers:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        _subscribers.remove(q)


def _next_stream_seq() -> int:
    global _stream_seq
    _stream_seq += 1
    return _stream_seq


async def _persist_and_broadcast(event: dict) -> None:
    if "timestamp" not in event:
        event["timestamp"] = int(time.time() * 1000)
    seq = _next_stream_seq()
    event["seq"] = seq
    _event_buffer.append(event)
    if _persist_buffer is not None:
        _persist_buffer.append_stream(
            StreamEventRow(
                seq=seq,
                type=event.get("type", ""),
                payload=event,
                timestamp_ms=int(event.get("timestamp") or 0),
                agent=event.get("agent"),
                session=event.get("session") or event.get("session_id"),
            ))
    await _broadcast(event)


async def _hydrate_relay_tail() -> None:
    if _store is None:
        return
    for evt in await _store.recent_stream_events(limit=2000):
        _event_buffer.append(evt)


async def _retention_loop() -> None:
    while True:
        await asyncio.sleep(300.0)
        if _store is None:
            continue
        try:
            await _store.prune_stream_events(STREAM_EVENT_RETENTION_MAX)
        except Exception:
            logger.exception("stream retention prune failed")


async def _rehydrate_console_workspaces() -> None:
    if _store is None:
        return
    for row in await _store.list_console_workspaces():
        if row["id"] not in _console_workspaces:
            _restore_console_workspace(row)


@app.post("/ingest")
async def ingest(request: Request) -> dict:
    body = await request.json()
    events = body if isinstance(body, list) else [body]
    for evt in events:
        await _persist_and_broadcast(evt)
    return {"accepted": len(events)}


async def _replay_stream_from_db(after: int):
    cur = after
    last = after
    while True:
        rows = await _store.query_stream_events(after_seq=cur, limit=500)
        if not rows:
            break
        for evt in rows:
            s = int(evt.get("seq") or 0)
            if s <= last:
                continue
            last = s
            cur = s
            yield s, f"data: {json.dumps(evt)}\n\n"
        if len(rows) < 500:
            break


async def _event_generator(
    queue: asyncio.Queue[dict],
    after: int,
) -> None:
    last = after
    yield ": connected\n\n"
    oldest = int(_event_buffer[0].get("seq", 0)) if _event_buffer else 0
    if _store is not None and after > 0 and (not _event_buffer
                                             or after < oldest - 1):
        async for s, chunk in _replay_stream_from_db(after):
            last = s
            yield chunk
    for evt in list(_event_buffer):
        s = int(evt.get("seq") or 0)
        if s > last:
            last = s
            yield f"data: {json.dumps(evt)}\n\n"
    while True:
        try:
            evt = await asyncio.wait_for(queue.get(), timeout=30.0)
            s = int(evt.get("seq") or 0)
            if s and s <= last:
                continue
            last = s or last
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


# ── Trace Explorer ─────────────────────────────────────────────────────


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
            span_events = conn.execute(
                "SELECT * FROM span_events WHERE span_id = ? ORDER BY timestamp_ms",
                (d["span_id"], ),
            ).fetchall()
            d["events"] = [dict(e) for e in span_events]
            for e in d["events"]:
                if e.get("attributes"):
                    e["attributes"] = json.loads(e["attributes"])
            spans.append(d)
        return {"trace_id": trace_id, "spans": spans}
    finally:
        conn.close()


# ── Eval Results ───────────────────────────────────────────────────────


def _list_results_files() -> list[dict]:
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


def _get_aggregate_files(scenario: str, sweep_id: str) -> dict:
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


@app.get("/api/results")
async def list_results() -> list[dict]:
    sweeps = _list_results_files()
    if _store is not None:
        seen = {(s["scenario"], s["sweep_id"]) for s in sweeps}
        for s in await _store.list_sweeps():
            if (s["scenario"], s["sweep_id"]) not in seen:
                sweeps.append({
                    "scenario": s["scenario"],
                    "sweep_id": s["sweep_id"],
                    "path": ""
                })
    return sweeps


@app.get("/api/results/{scenario}/{sweep_id}")
async def get_aggregate(scenario: str, sweep_id: str) -> dict:
    if _store is not None:
        agg = await _store.get_sweep_aggregate(scenario, sweep_id)
        if agg is not None:
            return agg
        cards = await _store.get_scorecards(scenario, sweep_id)
        if cards:
            return {"runs": cards, "n_runs": len(cards)}
    return _get_aggregate_files(scenario, sweep_id)


@app.get("/api/results/{scenario}/{sweep_id}/runs/{run_id}")
async def get_run(scenario: str, sweep_id: str, run_id: str) -> dict:
    if _store is not None:
        card = await _store.get_scorecard(scenario, sweep_id, run_id)
        if card is not None:
            return card
    run_dir = RESULTS_DIR / scenario / sweep_id / "runs" / run_id
    sc = run_dir / "scorecard.json"
    if sc.exists():
        return json.loads(sc.read_text())
    return {"error": "not found"}


# ── Portal Data Helpers ────────────────────────────────────────────────


def _load_json(rel: str) -> object:
    path = DISK_ROOT / rel
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _load_dir_jsons(rel: str) -> list[dict]:
    d = DISK_ROOT / rel
    if not d.exists() or not d.is_dir():
        return []
    results = []
    for f in sorted(d.iterdir()):
        if f.suffix == ".json":
            results.append(json.loads(f.read_text()))
    return results


def _load_dir_jsons_recursive(rel: str) -> list[dict]:
    d = DISK_ROOT / rel
    if not d.exists() or not d.is_dir():
        return []
    results = []
    for f in sorted(d.rglob("*.json")):
        results.append(json.loads(f.read_text()))
    return results


def _flatten_user(obj) -> str:
    if isinstance(obj, dict):
        return obj.get("name") or obj.get("login") or str(obj)
    return str(obj) if obj else ""


def _normalize_incident(raw: dict) -> dict:
    severity = raw.get("severity", "")
    if isinstance(severity, dict):
        severity = severity.get("value", "")
    service = raw.get("service", "")
    if isinstance(service, dict):
        service = service.get("name", "")
    assignee = ""
    assignments = raw.get("assignments", [])
    if assignments and isinstance(assignments[0], dict):
        a = assignments[0].get("assignee", {})
        assignee = a.get("name", "") if isinstance(a, dict) else str(a)
    elif raw.get("assignee"):
        assignee = _flatten_user(raw["assignee"])
    return {
        "id": raw.get("id", ""),
        "title": raw.get("title", ""),
        "status": raw.get("status", ""),
        "severity": severity,
        "service": service,
        "assignee": assignee,
        "created_at": raw.get("created_at", ""),
    }


def _normalize_deployment(raw: dict) -> dict:
    status = raw.get("status", "")
    statuses = raw.get("statuses", [])
    if statuses and isinstance(statuses[0], dict):
        status = statuses[0].get("state", "")
    return {
        "id": raw.get("id", ""),
        "ref": raw.get("ref", ""),
        "environment": raw.get("environment", ""),
        "created_at": raw.get("created_at", ""),
        "status": status,
        "creator": _flatten_user(raw.get("creator")),
    }


def _normalize_account(raw: dict) -> dict:
    out = dict(raw)
    out["csm"] = _flatten_user(raw.get("csm"))
    return out


def _normalize_escalation(raw: dict) -> dict:
    out = dict(raw)
    out["owner"] = _flatten_user(raw.get("owner"))
    return out


def _normalize_contract(raw: dict) -> dict:
    out = dict(raw)
    out["owner"] = _flatten_user(raw.get("owner"))
    return out


def _normalize_audit(raw: dict) -> dict:
    out = dict(raw)
    checklist = raw.get("checklist", [])
    normalized_cl = []
    for item in checklist:
        ni = dict(item)
        ni["owner"] = _flatten_user(item.get("owner"))
        status = ni.get("status", "")
        if status == "complete":
            ni["status"] = "completed"
        normalized_cl.append(ni)
    out["checklist"] = normalized_cl
    return out


# ── Portal: IT Helpdesk ───────────────────────────────────────────────


@app.get("/api/tickets/{queue}")
async def list_tickets(queue: str) -> list[dict]:
    return _load_dir_jsons_recursive(f"tickets/queues/{queue}")


@app.get("/api/tickets/{queue}/{ticket_id}")
async def get_ticket(queue: str, ticket_id: str) -> dict:
    base = DISK_ROOT / "tickets" / "queues" / queue
    if not base.exists():
        return {"error": "not found"}
    for f in base.rglob(f"{ticket_id}*.json"):
        return json.loads(f.read_text())
    return {"error": "not found"}


# ── Portal: HR ─────────────────────────────────────────────────────────


@app.get("/api/employees")
async def list_employees() -> list[dict]:
    return _load_dir_jsons("slack/users")


@app.get("/api/sheets/{sheet_id}")
async def get_sheet(sheet_id: str) -> dict:
    owned = DISK_ROOT / "sheets" / "owned"
    if owned.exists():
        for f in owned.iterdir():
            if sheet_id in f.name and f.suffix == ".json":
                return json.loads(f.read_text())
    return {"error": "not found"}


@app.get("/api/sheets")
async def list_sheets() -> list[dict]:
    return _load_dir_jsons("sheets/owned")


# ── Portal: Finance ───────────────────────────────────────────────────


@app.get("/api/finance/expenses")
async def list_expenses() -> list[dict]:
    return _load_dir_jsons_recursive("finance/expenses")


@app.get("/api/finance/purchase-orders")
async def list_purchase_orders() -> list[dict]:
    return _load_dir_jsons_recursive("finance/purchase_orders")


@app.get("/api/finance/invoices")
async def list_invoices() -> list[dict]:
    return _load_dir_jsons_recursive("finance/invoices")


@app.get("/api/finance/budgets")
async def get_budgets() -> dict:
    data = _load_json("finance/budgets/Q2_2026.json")
    if data is None:
        return {"departments": []}
    return data


# ── Portal: Engineering ───────────────────────────────────────────────


@app.get("/api/engineering/incidents")
async def list_incidents() -> list[dict]:
    raw = _load_dir_jsons_recursive("pagerduty/incidents")
    return [_normalize_incident(r) for r in raw]


@app.get("/api/engineering/deployments")
async def list_deployments() -> list[dict]:
    deploy_dir = DISK_ROOT / "github"
    if not deploy_dir.exists():
        return []
    results = []
    for f in sorted(deploy_dir.rglob("deployments/*.json")):
        results.append(_normalize_deployment(json.loads(f.read_text())))
    return results


@app.get("/api/engineering/metrics")
async def get_metrics() -> list[dict]:
    return _load_dir_jsons_recursive("datadog/metrics")


# ── Portal: Customer Support ──────────────────────────────────────────


@app.get("/api/customers/accounts")
async def list_accounts() -> list[dict]:
    raw = _load_dir_jsons("customers/accounts")
    return [_normalize_account(r) for r in raw]


@app.get("/api/customers/escalations")
async def list_escalations() -> list[dict]:
    raw = _load_dir_jsons("customers/escalations")
    return [_normalize_escalation(r) for r in raw]


@app.get("/api/customers/tickets")
async def list_customer_tickets() -> list[dict]:
    return _load_dir_jsons_recursive("tickets/queues/customer-support")


# ── Portal: Compliance ────────────────────────────────────────────────


@app.get("/api/compliance/contracts")
async def list_contracts() -> list[dict]:
    raw = _load_dir_jsons_recursive("compliance/contracts")
    return [_normalize_contract(r) for r in raw]


@app.get("/api/compliance/audits")
async def list_audits() -> list[dict]:
    raw = _load_dir_jsons("compliance/audits")
    return [_normalize_audit(r) for r in raw]


@app.get("/api/compliance/policies")
async def list_policies() -> list[dict]:
    return _load_dir_jsons("compliance/policies")


# ── Console: Agent Sessions ───────────────────────────────────────────

SYSTEM_PROMPT = """\
You are an enterprise operations agent with access to a virtual filesystem \
containing data from multiple departments: IT helpdesk, HR, Finance, \
Engineering/SRE, Customer Support, and Legal/Compliance.

You can run shell commands (ls, cat, head, grep, jq, find, tree) to explore \
the mounted data. Each department's data lives under a specific mount path.

Available commands:
- ls <path>  — list directory contents
- cat <path> — read file contents
- head -n N <path> — read first N lines
- grep <pattern> <path> — search for patterns
- find <path> -name "*.json" — find files
- jq <filter> <path> — parse JSON

When you want to run a command, output it on its own line starting with \
EXEC: followed by the command. For example:
EXEC: ls /tickets/queues/it-helpdesk/open/

You will receive the command output, then continue reasoning.

When you have gathered enough information, provide a clear, specific answer \
with ticket IDs, names, dates, and amounts from the actual data. Never \
fabricate information — only cite what you actually read.

If the user asks a follow-up question, use information you already gathered \
or run additional commands as needed.

Before any EXEC: command or your final answer, you may show your reasoning \
wrapped in <thinking>...</thinking> tags. Put the reasoning first, then the \
EXEC: commands or the final answer outside the tags.\
"""


@dataclass
class ChatEntry:
    role: str
    content: str
    timestamp: float = 0.0


@dataclass
class AgentSession:
    id: str
    services: list[str]
    status: str = "ready"
    created_at: float = 0.0
    chat_history: list[ChatEntry] = field(default_factory=list)
    workspace: object = field(default=None, repr=False)
    events: list[dict] = field(default_factory=list)
    agui_trace: list[dict] = field(default_factory=list)
    error: str | None = None
    kind: str = "agent"
    next_seq: int = 0
    persisted_msgs: int = 0


_sessions: dict[str, AgentSession] = {}
_openai_client = None


def _session_row(session: AgentSession) -> SessionRow:
    return SessionRow(
        id=session.id,
        services=list(session.services),
        status=session.status,
        created_at_ms=int((session.created_at or 0) * 1000),
        updated_at_ms=int(time.time() * 1000),
        has_workspace=session.workspace is not None,
        kind=session.kind,
        error=session.error,
    )


def _persist_session(session: AgentSession) -> None:
    if _persist_buffer is not None:
        _persist_buffer.put_session(_session_row(session))


def _persist_new_messages(session: AgentSession) -> None:
    if _persist_buffer is None:
        return
    for entry in session.chat_history[session.persisted_msgs:]:
        _persist_buffer.append_message(
            MessageRow(session_id=session.id,
                       role=entry.role,
                       content=entry.content,
                       timestamp_ms=int((entry.timestamp or 0) * 1000)))
    session.persisted_msgs = len(session.chat_history)


async def _make_coalescer(session: AgentSession):
    if _persist_buffer is None or _store is None:
        return None
    if session.next_seq <= 0:
        session.next_seq = await _store.next_seq(session.id)
    return StreamCoalescer(session.id, session.next_seq)


def _finish_coalescer(session: AgentSession, coalescer) -> None:
    if coalescer is not None and _persist_buffer is not None:
        _persist_buffer.add_feed(coalescer.finalize())
        session.next_seq = coalescer.next_seq
    _persist_new_messages(session)
    _persist_session(session)


def _get_openai_client():
    global _openai_client
    if AsyncOpenAI is None:
        raise RuntimeError("The 'openai' package is not installed. "
                           "Install it with: pip install openai")
    if _openai_client is None:
        _openai_client = AsyncOpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL
            if OPENAI_BASE_URL != "https://api.openai.com/v1" else None,
        )
    return _openai_client


async def _emit_event(session_id: str, event: dict) -> None:
    event["session_id"] = session_id
    if "timestamp" not in event:
        event["timestamp"] = int(time.time() * 1000)
    session = _sessions.get(session_id)
    if session:
        session.events.append(event)
    await _persist_and_broadcast(event)


def _build_workspace(services: list[str]):
    _ensure_fixture_disk()
    if build_l1_workspace is not None and _HAS_MIRAGE:
        try:
            return build_l1_workspace(
                disk_root=DISK_ROOT,
                agent_id="console-agent",
                session_id="default",
            )
        except Exception as exc:
            logger.warning(
                "L1 workspace build failed, using disk fallback: %s", exc)
    return _build_disk_workspace()


def _build_disk_workspace():
    if not DISK_ROOT.exists():
        logger.warning("DISK_ROOT %s does not exist", DISK_ROOT)
        return None
    if not _HAS_MIRAGE:
        logger.warning("mirage not installed, workspace unavailable")
        return None
    mounts: dict[str, tuple] = {
        "/": (RAMResource(), MountMode.WRITE),
    }
    for subdir in sorted(DISK_ROOT.iterdir()):
        if not subdir.is_dir() or subdir.name.startswith("."):
            continue
        mounts[f"/{subdir.name}"] = (DiskResource(root=str(subdir)),
                                     MountMode.READ)
    if len(mounts) <= 1:
        return None
    return Workspace(mounts, mode=MountMode.WRITE)


def _build_file_prompt(services: list[str]) -> str:
    sections = []
    mount_map = {
        "it": [
            "## IT Helpdesk\n/tickets/queues/it-helpdesk/{open,in_progress,resolved}/ — IT tickets (JSON)\n/sheets/owned/ — spreadsheets (hire tracker, access matrix, equipment)\n/gdocs/owned/ — runbooks, SLA docs, postmortems",
        ],
        "hr": [
            "## HR & People\n/sheets/owned/ — New Hire Tracker (SH101), PTO Calendar (SH104)\n/slack/channels/onboarding__C302/ — onboarding channel\n/slack/dms/ — direct messages",
        ],
        "finance": [
            "## Finance\n/finance/expenses/{pending,approved,rejected}/ — expense reports (JSON)\n/finance/purchase_orders/{open,approved,received}/ — POs (JSON)\n/finance/invoices/{pending,paid,disputed}/ — invoices (JSON)\n/finance/budgets/Q2_2026.json — department budgets",
        ],
        "engineering": [
            "## Engineering / SRE\n/pagerduty/incidents/{triggered,acknowledged,resolved}/ — PagerDuty incidents\n/pagerduty/services/ — service definitions\n/github/repos/northhill/platform-api/{deployments,commits,pulls}/ — GitHub\n/datadog/logs/platform-api/ — application logs\n/datadog/metrics/platform-api/ — metrics time series",
        ],
        "support": [
            "## Customer Support\n/customers/accounts/ — customer accounts with health scores\n/customers/escalations/ — active escalations\n/tickets/queues/customer-support/{open,in_progress,resolved}/ — support tickets",
        ],
        "compliance": [
            "## Compliance & Legal\n/compliance/contracts/{in_review,active,expired}/ — contracts\n/compliance/audits/ — audit checklists (SOC2, GDPR)\n/compliance/policies/ — policies with acknowledgment tracking\n/tickets/queues/legal/{open,in_progress,resolved}/ — legal tickets",
        ],
    }
    for svc in services:
        if svc in mount_map:
            sections.extend(mount_map[svc])
    if not sections:
        sections.append("All departments are available. Start with: ls /")
    return "# Available Data\n\n" + "\n\n".join(sections)


async def _execute_in_workspace_detailed(
    ws,
    command: str,
    session_id: str,
) -> tuple[str, int, list]:
    try:
        ops_before = len(getattr(ws.ops, "records", None) or [])
        result = await ws.execute(command, session_id="default")
        stdout = (result.stdout or b"").decode(errors="replace")
        stderr = (result.stderr or b"").decode(errors="replace")
        exit_code = getattr(result, "exit_code", 0) or 0
        await _emit_event(
            session_id, {
                "type": "command",
                "agent": "console-agent",
                "session": session_id,
                "command": command,
                "exit_code": exit_code,
                "stdout": stdout[:4096],
            })
        all_records = getattr(ws.ops, "records", None) or []
        new_records = list(all_records[ops_before:])
        for rec in new_records:
            await _emit_event(
                session_id, {
                    "type": "op",
                    "agent": "console-agent",
                    "session": session_id,
                    "op": rec.op,
                    "path": rec.path,
                    "source": rec.source,
                    "bytes": rec.bytes,
                    "duration_ms": rec.duration_ms,
                    "mount_prefix": rec.mount_prefix,
                    "fingerprint": rec.fingerprint,
                    "revision": rec.revision,
                    "is_cache": rec.source == "ram",
                })
        output = stdout.rstrip()
        if stderr.strip():
            output += f"\n[stderr] {stderr.rstrip()}"
        if exit_code != 0:
            output += f"\n[exit_code={exit_code}]"
        return output or "(no output)", exit_code, new_records
    except Exception as exc:
        return f"[error] {type(exc).__name__}: {exc}", 1, []


async def _execute_in_workspace(ws, command: str, session_id: str) -> str:
    output, _exit_code, _ops = await _execute_in_workspace_detailed(
        ws, command, session_id)
    return output


async def _run_conversation_turn(
    session: AgentSession,
    user_message: str,
) -> str:
    session.status = "running"
    session.chat_history.append(
        ChatEntry(role="user", content=user_message, timestamp=time.time()))
    await _emit_event(session.id, {
        "type": "agent_status",
        "status": "running",
        "task": user_message[:200],
    })
    file_prompt = _build_file_prompt(session.services)
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT + "\n\n" + file_prompt
        },
    ]
    for entry in session.chat_history:
        messages.append({
            "role": entry.role if entry.role != "agent" else "assistant",
            "content": entry.content
        })
    max_iterations = 15
    for _ in range(max_iterations):
        try:
            client = _get_openai_client()
            resp = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                max_tokens=4096,
            )
            assistant_text = resp.choices[0].message.content or ""
        except RuntimeError as exc:
            error_msg = str(exc)
            session.status = "ready"
            session.chat_history.append(
                ChatEntry(role="agent",
                          content=error_msg,
                          timestamp=time.time()))
            await _emit_event(session.id, {
                "type": "agent_status",
                "status": "error",
                "error": error_msg,
            })
            return error_msg
        except Exception as exc:
            error_msg = f"LLM error: {type(exc).__name__}: {exc}"
            session.status = "ready"
            session.chat_history.append(
                ChatEntry(role="agent",
                          content=error_msg,
                          timestamp=time.time()))
            await _emit_event(session.id, {
                "type": "agent_status",
                "status": "error",
                "error": error_msg,
            })
            return error_msg
        exec_lines = [
            line[5:].strip() for line in assistant_text.splitlines()
            if line.strip().startswith("EXEC:")
        ]
        if not exec_lines:
            session.chat_history.append(
                ChatEntry(role="agent",
                          content=assistant_text,
                          timestamp=time.time()))
            session.status = "ready"
            await _emit_event(session.id, {
                "type": "agent_status",
                "status": "completed",
            })
            return assistant_text
        messages.append({"role": "assistant", "content": assistant_text})
        command_outputs = []
        for cmd in exec_lines:
            await _emit_event(session.id, {
                "type": "agent_thinking",
                "message": f"Running: {cmd}",
            })
            if session.workspace:
                output = await _execute_in_workspace(session.workspace, cmd,
                                                     session.id)
            else:
                output = (
                    "(workspace not available — run "
                    "`uv run mirage-eval seed --scenario northhill_corp` "
                    "to generate fixture data)")
            command_outputs.append(f"$ {cmd}\n{output}")
        combined_output = "\n\n".join(command_outputs)
        messages.append({
            "role":
            "user",
            "content":
            f"Command output:\n```\n{combined_output}\n```"
        })
    final = "Reached maximum iterations. Here is what I found so far."
    session.chat_history.append(
        ChatEntry(role="agent", content=final, timestamp=time.time()))
    session.status = "ready"
    return final


def _extract_reasoning_delta(delta) -> str | None:
    for attr in ("reasoning_content", "reasoning"):
        val = getattr(delta, attr, None)
        if val:
            return val
    return None


_THINK_OPEN = ("<thinking>", "<think>")
_THINK_CLOSE = ("</thinking>", "</think>")


def _earliest_marker(text: str, markers: tuple[str, ...]) -> tuple[int, str]:
    best = -1
    found = ""
    for m in markers:
        i = text.find(m)
        if i != -1 and (best == -1 or i < best):
            best = i
            found = m
    return best, found


def _partial_tail(text: str, markers: tuple[str, ...]) -> int:
    longest = max(len(m) for m in markers)
    for length in range(min(longest - 1, len(text)), 0, -1):
        suffix = text[len(text) - length:]
        for m in markers:
            if m.startswith(suffix):
                return length
    return 0


def _route_think(state: dict, delta: str) -> list[tuple[str, str]]:
    text = state["carry"] + delta
    state["carry"] = ""
    segments: list[tuple[str, str]] = []
    while text:
        if state["in_think"]:
            idx, tag = _earliest_marker(text, _THINK_CLOSE)
            if idx == -1:
                tail = _partial_tail(text, _THINK_CLOSE)
                if tail:
                    state["carry"] = text[len(text) - tail:]
                    text = text[:len(text) - tail]
                if text:
                    segments.append(("think", text))
                break
            if idx > 0:
                segments.append(("think", text[:idx]))
            state["in_think"] = False
            text = text[idx + len(tag):]
        else:
            idx, tag = _earliest_marker(text, _THINK_OPEN)
            if idx == -1:
                tail = _partial_tail(text, _THINK_OPEN)
                if tail:
                    state["carry"] = text[len(text) - tail:]
                    text = text[:len(text) - tail]
                if text:
                    segments.append(("body", text))
                break
            if idx > 0:
                segments.append(("body", text[:idx]))
            state["in_think"] = True
            text = text[idx + len(tag):]
    return segments


async def _run_conversation_turn_stream(
    session: AgentSession,
    user_message: str,
):
    run_id = f"run-{uuid.uuid4()}"
    yield {
        "type": "RUN_STARTED",
        "timestamp": int(time.time() * 1000),
        "thread_id": session.id,
        "run_id": run_id,
    }
    session.status = "running"
    session.chat_history.append(
        ChatEntry(role="user", content=user_message, timestamp=time.time()))
    await _emit_event(session.id, {
        "type": "agent_status",
        "status": "running",
        "task": user_message[:200],
    })
    file_prompt = _build_file_prompt(session.services)
    messages: list[dict] = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT + "\n\n" + file_prompt,
        },
    ]
    for entry in session.chat_history:
        messages.append({
            "role": entry.role if entry.role != "agent" else "assistant",
            "content": entry.content,
        })
    try:
        step_num = 0
        final_text = ""
        max_iterations = 15
        for _ in range(max_iterations):
            step_num += 1
            step_id = f"step-{step_num}"
            yield {
                "type": "STEP_STARTED",
                "timestamp": int(time.time() * 1000),
                "step_id": step_id,
                "step_name": f"Iteration {step_num}",
            }
            client = _get_openai_client()
            msg_id = f"msg-{uuid.uuid4()}"
            assistant_text = ""
            thinking_id = ""
            thinking_open = False
            text_open = False
            think_state = {"in_think": False, "carry": ""}
            create_kwargs = {
                "model": OPENAI_MODEL,
                "messages": messages,
                "max_tokens": 4096,
                "stream": True,
            }
            if OPENAI_REASONING:
                create_kwargs["extra_body"] = {"reasoning": {"enabled": True}}
            stream = await client.chat.completions.create(**create_kwargs)
            async for chunk in stream:
                if not chunk.choices:
                    continue
                ch_delta = chunk.choices[0].delta
                rdelta = _extract_reasoning_delta(ch_delta)
                if rdelta:
                    if not thinking_open:
                        thinking_id = f"think-{uuid.uuid4()}"
                        yield {
                            "type": "THINKING_START",
                            "timestamp": int(time.time() * 1000),
                            "thinking_id": thinking_id,
                            "step_id": step_id,
                        }
                        thinking_open = True
                    yield {
                        "type": "THINKING_CONTENT",
                        "timestamp": int(time.time() * 1000),
                        "thinking_id": thinking_id,
                        "delta": rdelta,
                    }
                content = getattr(ch_delta, "content", None)
                if not content:
                    continue
                for kind, seg in _route_think(think_state, content):
                    if kind == "think":
                        if not thinking_open:
                            thinking_id = f"think-{uuid.uuid4()}"
                            yield {
                                "type": "THINKING_START",
                                "timestamp": int(time.time() * 1000),
                                "thinking_id": thinking_id,
                                "step_id": step_id,
                            }
                            thinking_open = True
                        yield {
                            "type": "THINKING_CONTENT",
                            "timestamp": int(time.time() * 1000),
                            "thinking_id": thinking_id,
                            "delta": seg,
                        }
                        continue
                    if thinking_open:
                        yield {
                            "type": "THINKING_END",
                            "timestamp": int(time.time() * 1000),
                            "thinking_id": thinking_id,
                        }
                        thinking_open = False
                    if not text_open:
                        yield {
                            "type": "TEXT_MESSAGE_START",
                            "timestamp": int(time.time() * 1000),
                            "message_id": str(msg_id),
                            "role": "assistant",
                        }
                        text_open = True
                    assistant_text += seg
                    yield {
                        "type": "TEXT_MESSAGE_CONTENT",
                        "timestamp": int(time.time() * 1000),
                        "message_id": str(msg_id),
                        "delta": seg,
                    }
            if think_state["carry"]:
                tail = think_state["carry"]
                if not text_open:
                    yield {
                        "type": "TEXT_MESSAGE_START",
                        "timestamp": int(time.time() * 1000),
                        "message_id": str(msg_id),
                        "role": "assistant",
                    }
                    text_open = True
                assistant_text += tail
                yield {
                    "type": "TEXT_MESSAGE_CONTENT",
                    "timestamp": int(time.time() * 1000),
                    "message_id": str(msg_id),
                    "delta": tail,
                }
            if thinking_open:
                yield {
                    "type": "THINKING_END",
                    "timestamp": int(time.time() * 1000),
                    "thinking_id": thinking_id,
                }
                thinking_open = False
            exec_lines = [
                line[5:].strip() for line in assistant_text.splitlines()
                if line.strip().startswith("EXEC:")
            ]
            if not exec_lines:
                if text_open:
                    yield {
                        "type": "TEXT_MESSAGE_END",
                        "timestamp": int(time.time() * 1000),
                        "message_id": str(msg_id),
                    }
                final_text = assistant_text
                yield {
                    "type": "STEP_FINISHED",
                    "timestamp": int(time.time() * 1000),
                    "step_id": step_id,
                }
                break
            if text_open:
                yield {
                    "type": "TEXT_MESSAGE_END",
                    "timestamp": int(time.time() * 1000),
                    "message_id": str(msg_id),
                }
            messages.append({"role": "assistant", "content": assistant_text})
            command_outputs: list[str] = []
            for cmd in exec_lines:
                tc_id = f"tc-{uuid.uuid4()}"
                yield {
                    "type": "TOOL_CALL_START",
                    "timestamp": int(time.time() * 1000),
                    "tool_call_id": tc_id,
                    "tool_name": "exec",
                }
                yield {
                    "type": "TOOL_CALL_ARGS",
                    "timestamp": int(time.time() * 1000),
                    "tool_call_id": tc_id,
                    "delta": cmd,
                }
                if session.workspace:
                    output, exit_code, new_ops = (
                        await
                        _execute_in_workspace_detailed(session.workspace, cmd,
                                                       session.id))
                    for rec in new_ops:
                        yield {
                            "type": "CUSTOM",
                            "timestamp": int(time.time() * 1000),
                            "name": "vfs_op",
                            "value": {
                                "op": rec.op,
                                "path": rec.path,
                                "bytes": rec.bytes,
                                "mount_prefix": rec.mount_prefix,
                                "source": rec.source,
                                "duration_ms": rec.duration_ms,
                                "fingerprint": rec.fingerprint,
                                "revision": rec.revision,
                                "is_cache": rec.source == "ram",
                                "tool_call_id": tc_id,
                                "step_id": step_id,
                                "run_id": run_id,
                            },
                        }
                else:
                    output = (
                        "(workspace not available — run "
                        "`uv run mirage-eval seed --scenario northhill_corp` "
                        "to generate fixture data)")
                    exit_code = 1
                yield {
                    "type": "TOOL_CALL_RESULT",
                    "timestamp": int(time.time() * 1000),
                    "tool_call_id": tc_id,
                    "result": output,
                    "exit_code": exit_code,
                }
                yield {
                    "type": "TOOL_CALL_END",
                    "timestamp": int(time.time() * 1000),
                    "tool_call_id": tc_id,
                }
                command_outputs.append(f"$ {cmd}\n{output}")
            combined_output = "\n\n".join(command_outputs)
            messages.append({
                "role":
                "user",
                "content":
                f"Command output:\n```\n{combined_output}\n```",
            })
            yield {
                "type": "STEP_FINISHED",
                "timestamp": int(time.time() * 1000),
                "step_id": step_id,
            }
        else:
            final_text = (
                "Reached maximum iterations. Here is what I found so far.")
        session.chat_history.append(
            ChatEntry(role="agent", content=final_text, timestamp=time.time()))
        session.status = "ready"
        await _emit_event(session.id, {
            "type": "agent_status",
            "status": "completed",
        })
    except Exception as exc:
        error_msg = f"Error: {type(exc).__name__}: {exc}"
        session.chat_history.append(
            ChatEntry(role="agent", content=error_msg, timestamp=time.time()))
        session.status = "ready"
        await _emit_event(session.id, {
            "type": "agent_status",
            "status": "error",
            "error": error_msg,
        })
        yield {
            "type": "RUN_ERROR",
            "timestamp": int(time.time() * 1000),
            "thread_id": session.id,
            "run_id": run_id,
            "error": error_msg,
        }
        return
    yield {
        "type": "RUN_FINISHED",
        "timestamp": int(time.time() * 1000),
        "thread_id": session.id,
        "run_id": run_id,
    }


def _record_agui_event(session: AgentSession, event: dict) -> None:
    session.agui_trace.append(event)


async def _stream_agui_events(
    session: AgentSession,
    user_message: str,
):
    coalescer = await _make_coalescer(session)
    try:
        async for event in _run_conversation_turn_stream(
                session, user_message):
            _record_agui_event(session, event)
            if coalescer is not None:
                _persist_buffer.add_feed(coalescer.feed(event))
            yield f"data: {json.dumps(event)}\n\n"
    finally:
        _finish_coalescer(session, coalescer)


async def _stream_no_key_response(
    session: AgentSession,
    user_message: str,
):
    ts = int(time.time() * 1000)
    run_id = f"run-{uuid.uuid4()}"
    msg_id = f"msg-{uuid.uuid4()}"
    msg = ("OPENAI_API_KEY is not set. Please set it in your environment "
           "to enable the agent. You can still explore the data through "
           "the Portal tab.")
    session.chat_history.append(
        ChatEntry(role="user", content=user_message, timestamp=time.time()))
    session.chat_history.append(
        ChatEntry(role="agent", content=msg, timestamp=time.time()))
    coalescer = await _make_coalescer(session)
    for event in [
        {
            "type": "RUN_STARTED",
            "timestamp": ts,
            "thread_id": session.id,
            "run_id": run_id,
        },
        {
            "type": "TEXT_MESSAGE_START",
            "timestamp": ts,
            "message_id": str(msg_id),
            "role": "assistant",
        },
        {
            "type": "TEXT_MESSAGE_CONTENT",
            "timestamp": ts,
            "message_id": str(msg_id),
            "delta": msg,
        },
        {
            "type": "TEXT_MESSAGE_END",
            "timestamp": ts,
            "message_id": str(msg_id),
        },
        {
            "type": "RUN_FINISHED",
            "timestamp": ts,
            "thread_id": session.id,
            "run_id": run_id,
        },
    ]:
        _record_agui_event(session, event)
        if coalescer is not None:
            _persist_buffer.add_feed(coalescer.feed(event))
        yield f"data: {json.dumps(event)}\n\n"
    _finish_coalescer(session, coalescer)


@app.post("/api/sessions")
async def create_session(request: Request) -> dict:
    body = await request.json()
    session_id = str(uuid.uuid4())[:8]
    services = body.get("services", [])
    ws = _build_workspace(services)
    session = AgentSession(
        id=session_id,
        services=services,
        created_at=time.time(),
        workspace=ws,
    )
    _sessions[session_id] = session
    _persist_session(session)
    return {
        "id": session_id,
        "status": session.status,
        "services": session.services,
        "has_workspace": ws is not None,
    }


@app.post("/api/sessions/{session_id}/message")
async def send_message(session_id: str, request: Request) -> dict:
    session = _sessions.get(session_id)
    if not session:
        return JSONResponse({"error": "session not found"}, status_code=404)
    if session.status == "running":
        return JSONResponse({"error": "agent is still processing"},
                            status_code=409)
    body = await request.json()
    user_message = body.get("message", "").strip()
    if not user_message:
        return JSONResponse({"error": "message required"}, status_code=400)
    if not OPENAI_API_KEY:
        reply = (
            "OPENAI_API_KEY is not set. Please set it in your environment "
            "to enable the agent. You can still explore the data through "
            "the Portal tab.")
        session.chat_history.append(
            ChatEntry(role="user", content=user_message,
                      timestamp=time.time()))
        session.chat_history.append(
            ChatEntry(role="agent", content=reply, timestamp=time.time()))
        _persist_new_messages(session)
        _persist_session(session)
        return {"reply": reply, "status": "ready"}
    reply = await _run_conversation_turn(session, user_message)
    _persist_new_messages(session)
    _persist_session(session)
    return {"reply": reply, "status": session.status}


_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


@app.post("/api/sessions/{session_id}/message/stream")
async def send_message_stream(session_id: str,
                              request: Request) -> StreamingResponse:
    session = _sessions.get(session_id)
    if not session:
        return JSONResponse({"error": "session not found"}, status_code=404)
    if session.status == "running":
        return JSONResponse({"error": "agent is still processing"},
                            status_code=409)
    body = await request.json()
    user_message = body.get("message", "").strip()
    if not user_message:
        return JSONResponse({"error": "message required"}, status_code=400)
    if not OPENAI_API_KEY:
        return StreamingResponse(
            _stream_no_key_response(session, user_message),
            media_type="text/event-stream",
            headers=_SSE_HEADERS,
        )
    return StreamingResponse(
        _stream_agui_events(session, user_message),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


@app.get("/api/sessions/{session_id}/history")
async def session_history(session_id: str) -> list[dict]:
    session = _sessions.get(session_id)
    if session is not None:
        return [{
            "role": e.role,
            "content": e.content,
            "timestamp": e.timestamp
        } for e in session.chat_history]
    if _store is not None:
        rows = await _store.get_history(session_id)
        if rows or await _store.get_session(session_id) is not None:
            return rows
    return JSONResponse({"error": "not found"}, status_code=404)


@app.get("/api/sessions/{session_id}/trace")
async def session_trace(session_id: str, after: int = 0) -> dict:
    session = _sessions.get(session_id)
    if session is not None:
        events = session.agui_trace
        return {
            "session_id": session_id,
            "events": events,
            "event_count": len(events),
        }
    if _store is not None and await _store.get_session(session_id) is not None:
        events = await _store.get_trace(session_id, after_seq=after)
        return {
            "session_id": session_id,
            "events": events,
            "event_count": len(events),
        }
    return JSONResponse({"error": "not found"}, status_code=404)


def _replay_action(idx: int, o: dict) -> dict:
    return {
        "idx": idx,
        "op": o["op"],
        "path": o["path"],
        "source": o["source"],
        "bytes": o["bytes"],
        "duration_ms": o["duration_ms"],
        "mount_prefix": o["mount_prefix"],
        "fingerprint": o.get("fingerprint"),
        "revision": o.get("revision"),
        "is_cache": o["source"] == "ram",
        "tool_call_id": o.get("tool_call_id"),
        "run_id": o.get("run_id"),
        "timestamp": o["timestamp_ms"],
    }


def _fold_replay_state(actions: list[dict], cursor: int) -> dict:
    write_ops = {"write", "append", "create", "truncate", "unlink", "rename"}
    read_ops = {"read", "stream"}
    overlay: dict[str, dict] = {}
    reads: dict[str, dict] = {}
    for a in actions[:cursor + 1]:
        if a["op"] in write_ops:
            overlay[a["path"]] = {
                "path": a["path"],
                "op": a["op"],
                "bytes": a["bytes"],
                "mount_prefix": a["mount_prefix"],
            }
        elif a["op"] in read_ops:
            reads[a["path"]] = {
                "path": a["path"],
                "source": a["source"],
                "bytes": a["bytes"],
                "fingerprint": a["fingerprint"],
            }
    cur = actions[cursor] if 0 <= cursor < len(actions) else None
    diff = None
    if cur is not None and cur["op"] in write_ops:
        diff = {
            "kind": "write",
            "path": cur["path"],
            "added_bytes": cur["bytes"],
            "mount_prefix": cur["mount_prefix"],
        }
    elif cur is not None:
        diff = {
            "kind": "read",
            "path": cur["path"],
            "source": cur["source"],
            "is_cache": cur["is_cache"],
            "fingerprint": cur["fingerprint"],
            "revision": cur["revision"],
        }
    return {
        "overlay": list(overlay.values()),
        "reads_so_far": sorted(reads.keys()),
        "reads_count": len(reads),
        "cursor_op": cur,
        "diff": diff,
    }


@app.get("/api/sessions/{session_id}/replay")
async def session_replay(session_id: str,
                         cursor: int = -1,
                         run_id: str | None = None) -> dict:
    if _store is None:
        return JSONResponse({"error": "persistence not configured"},
                            status_code=503)
    ops = await _store.get_vfs_ops(session_id, run_id)
    total = len(ops)
    actions = [_replay_action(i, o) for i, o in enumerate(ops)]
    if total == 0:
        return {
            "session_id": session_id,
            "run_id": run_id,
            "cursor": -1,
            "total": 0,
            "actions": [],
            "state": _fold_replay_state(actions, -1),
        }
    if cursor < 0 or cursor >= total:
        cursor = total - 1
    return {
        "session_id": session_id,
        "run_id": run_id,
        "cursor": cursor,
        "total": total,
        "actions": actions,
        "state": _fold_replay_state(actions, cursor),
    }


@app.get("/api/sessions/{session_id}/status")
async def session_status(session_id: str) -> dict:
    session = _sessions.get(session_id)
    if session is not None:
        return {
            "id": session.id,
            "status": session.status,
            "services": session.services,
            "created_at": session.created_at,
            "message_count": len(session.chat_history),
            "has_workspace": session.workspace is not None,
            "error": session.error,
        }
    if _store is not None:
        row = await _store.get_session(session_id)
        if row is not None:
            return {
                "id": row["id"],
                "status": row["status"],
                "services": row["services"],
                "created_at": (row["created_at_ms"] or 0) / 1000.0,
                "message_count": len(await _store.get_history(session_id)),
                "has_workspace": bool(row["has_workspace"]),
                "error": row["error"],
            }
    return JSONResponse({"error": "not found"}, status_code=404)


def _live_session_entry(s: AgentSession) -> dict:
    return {
        "id": s.id,
        "status": s.status,
        "services": s.services,
        "created_at": s.created_at,
        "message_count": len(s.chat_history),
        "last_message":
        s.chat_history[-1].content[:100] if s.chat_history else "",
        "has_workspace": s.workspace is not None,
    }


@app.get("/api/sessions")
async def list_sessions() -> list[dict]:
    merged: dict[str, dict] = {}
    if _store is not None:
        for row in await _store.list_sessions():
            merged[row["id"]] = row
    for s in _sessions.values():
        merged[s.id] = _live_session_entry(s)
    return sorted(merged.values(),
                  key=lambda x: x.get("created_at", 0),
                  reverse=True)


# ── Investigations ─────────────────────────────────────────────────────

_INV_FIELD_MAP = {
    "title": "title",
    "templateId": "template_id",
    "severity": "severity",
    "status": "status",
    "trigger": "trigger",
    "triggerRef": "trigger_ref",
    "authority": "authority",
    "brief": "brief",
    "resolution": "resolution",
    "resolvedAt": "resolved_at_ms",
    "escalatedTo": "escalated_to",
}


def _inv_row_to_meta(row: dict) -> dict:
    return {
        "sessionId": row["session_id"],
        "title": row["title"],
        "templateId": row["template_id"],
        "severity": row["severity"],
        "status": row["status"],
        "trigger": row["trigger"],
        "triggerRef": row.get("trigger_ref"),
        "authority": row["authority"],
        "brief": row.get("brief"),
        "resolution": row.get("resolution"),
        "resolvedAt": row.get("resolved_at_ms"),
        "escalatedTo": row.get("escalated_to"),
        "createdAt": row["created_at_ms"],
        "updatedAt": row["updated_at_ms"],
    }


def _inv_pick(existing: dict | None,
              body: dict,
              camel: str,
              col: str,
              default=None):
    if body.get(camel) is not None:
        return body[camel]
    if existing is not None and existing.get(col) is not None:
        return existing.get(col)
    return default


def _inv_values(existing: dict | None, body: dict, now_ms: int) -> dict:
    return {
        "session_id":
        body["sessionId"],
        "title":
        _inv_pick(existing, body, "title", "title", "Untitled investigation"),
        "template_id":
        _inv_pick(existing, body, "templateId", "template_id", "custom"),
        "severity":
        _inv_pick(existing, body, "severity", "severity", "P3"),
        "status":
        _inv_pick(existing, body, "status", "status", "running"),
        "trigger":
        _inv_pick(existing, body, "trigger", "trigger", "manual"),
        "trigger_ref":
        _inv_pick(existing, body, "triggerRef", "trigger_ref"),
        "authority":
        _inv_pick(existing, body, "authority", "authority", "read_only"),
        "brief":
        _inv_pick(existing, body, "brief", "brief"),
        "resolution":
        _inv_pick(existing, body, "resolution", "resolution"),
        "resolved_at_ms":
        _inv_pick(existing, body, "resolvedAt", "resolved_at_ms"),
        "escalated_to":
        _inv_pick(existing, body, "escalatedTo", "escalated_to"),
        "created_at_ms":
        existing.get("created_at_ms") if existing else now_ms,
        "updated_at_ms":
        now_ms,
    }


def _inv_patch_fields(body: dict, now_ms: int) -> dict:
    fields = {
        col: body[camel]
        for camel, col in _INV_FIELD_MAP.items() if camel in body
    }
    fields["updated_at_ms"] = now_ms
    return fields


@app.get("/api/investigations")
async def list_investigations(status: str | None = None) -> list[dict]:
    if _store is None:
        return []
    rows = await _store.list_investigations(status=status)
    return [_inv_row_to_meta(r) for r in rows]


@app.post("/api/investigations")
async def upsert_investigation(request: Request):
    if _store is None:
        return JSONResponse({"error": "store unavailable"}, status_code=503)
    body = await _safe_json(request)
    if not body.get("sessionId"):
        return JSONResponse({"error": "sessionId required"}, status_code=400)
    existing = await _store.get_investigation(body["sessionId"])
    values = _inv_values(existing, body, int(time.time() * 1000))
    row = await _store.upsert_investigation(values)
    return _inv_row_to_meta(row)


@app.get("/api/investigations/{session_id}")
async def get_investigation(session_id: str):
    if _store is not None:
        row = await _store.get_investigation(session_id)
        if row is not None:
            return _inv_row_to_meta(row)
    return JSONResponse({"error": "not found"}, status_code=404)


@app.patch("/api/investigations/{session_id}")
async def patch_investigation(session_id: str, request: Request):
    if _store is None:
        return JSONResponse({"error": "store unavailable"}, status_code=503)
    body = await _safe_json(request)
    fields = _inv_patch_fields(body, int(time.time() * 1000))
    row = await _store.patch_investigation(session_id, fields)
    if row is None:
        return JSONResponse({"error": "not found"}, status_code=404)
    return _inv_row_to_meta(row)


@app.delete("/api/investigations/{session_id}")
async def delete_investigation(session_id: str):
    if _store is not None:
        await _store.delete_investigation(session_id)
    return {"deleted": session_id}


def _parse_ls_output(output: str) -> list[dict]:
    entries: list[dict] = []
    for line in output.strip().splitlines():
        if line.startswith("total ") or not line.strip():
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        perms = parts[0]
        name = parts[-1]
        if name in (".", ".."):
            continue
        entry_type = "dir" if perms.startswith("d") else "file"
        size = 0
        if len(parts) >= 5 and parts[4].isdigit():
            size = int(parts[4])
        entries.append({"name": name, "type": entry_type, "size": size})
    return entries


@app.get("/api/sessions/{session_id}/vfs")
async def vfs_list(session_id: str, path: str = "/") -> dict:
    session = _sessions.get(session_id)
    if not session:
        return JSONResponse({"error": "session not found"}, status_code=404)
    if not session.workspace:
        return JSONResponse({"error": "workspace not available"},
                            status_code=400)
    output = await _execute_in_workspace(session.workspace, f"ls -la {path}",
                                         session.id)
    entries = _parse_ls_output(output)
    return {"entries": entries}


@app.get("/api/sessions/{session_id}/vfs/file")
async def vfs_file(session_id: str, path: str = "/") -> dict:
    session = _sessions.get(session_id)
    if not session:
        return JSONResponse({"error": "session not found"}, status_code=404)
    if not session.workspace:
        return JSONResponse({"error": "workspace not available"},
                            status_code=400)
    content = await _execute_in_workspace(session.workspace, f"cat {path}",
                                          session.id)
    return {"content": content, "size": len(content), "path": path}


@app.get("/api/quick-actions")
async def quick_actions() -> list[dict]:
    return [
        {
            "id":
            "triage",
            "label":
            "Triage IT helpdesk queue",
            "services": ["it", "hr"],
            "task":
            "Triage all open IT helpdesk tickets. List each one with its priority, classify by severity, find any duplicates, and identify tickets needing escalation."
        },
        {
            "id":
            "onboarding",
            "label":
            "Check onboarding status",
            "services": ["it", "hr"],
            "task":
            "Look up Alex Rivera's onboarding status. Check the New Hire Tracker spreadsheet, any open IT tickets for Alex, and relevant Slack messages."
        },
        {
            "id":
            "incident",
            "label":
            "Investigate platform incident",
            "services": ["engineering"],
            "task":
            "Investigate the active platform-api incident. Check PagerDuty for triggered incidents, correlate with recent deployments, check Datadog logs for errors, and identify root cause."
        },
        {
            "id":
            "expenses",
            "label":
            "Review pending expenses",
            "services": ["finance"],
            "task":
            "Review all pending expense reports. List each with submitter, amount, category, and flag any that exceed policy limits or are missing details. Summarize totals by department."
        },
        {
            "id":
            "escalations",
            "label":
            "Handle customer escalations",
            "services": ["support", "engineering"],
            "task":
            "Review active customer escalations and at-risk accounts. Check account health scores, open support tickets, and cross-reference with any engineering incidents that may be affecting customers."
        },
        {
            "id":
            "audit",
            "label":
            "SOC2 audit status",
            "services": ["compliance"],
            "task":
            "Check the SOC2 audit progress. List all checklist items with their completion status, identify blockers, and check policy acknowledgment rates."
        },
        {
            "id":
            "full",
            "label":
            "Full enterprise review",
            "services":
            ["it", "hr", "finance", "engineering", "support", "compliance"],
            "task":
            "Do a comprehensive cross-department review. Check IT tickets, onboarding status, pending expenses, active incidents, customer health, and compliance audit progress. Give me an executive summary."
        },
    ]


@app.get("/api/config")
async def get_config() -> dict:
    return {
        "has_api_key": bool(OPENAI_API_KEY),
        "openai_available": AsyncOpenAI is not None,
        "model": OPENAI_MODEL,
        "base_url": OPENAI_BASE_URL,
        "reasoning": OPENAI_REASONING,
    }


# ── Console: Workspaces (dev dog-food loop) ───────────────────────────

_CONSOLE_SNAP_DIR = (Path(CONSOLE_SNAP_DIR) if CONSOLE_SNAP_DIR else
                     Path(tempfile.gettempdir()) / "arcadia_console_snapshots")
_WRITE_OP_NAMES = {
    "write", "unlink", "rmdir", "mkdir", "rename", "truncate", "create",
    "append"
}
_EFFECT_BY_PREFIX = {
    "slack": "external-effect",
    "linear": "external-effect",
    "gmail": "external-effect",
    "email": "external-effect",
    "github": "external-effect",
    "pagerduty": "external-effect",
    "discord": "external-effect",
    "telegram": "external-effect",
    "trello": "external-effect",
    "postgres": "system-of-record",
    "mongodb": "system-of-record",
    "customers": "system-of-record",
    "finance": "system-of-record",
    "datadog": "durable-internal",
    "s3": "durable-internal",
    "tickets": "durable-internal",
    "compliance": "durable-internal",
    "sheets": "durable-internal",
    "gdocs": "durable-internal",
    "gdrive": "durable-internal",
    "notion": "durable-internal",
    "hr": "durable-internal",
    "scratch": "scratch",
    "tmp": "scratch",
}
_EFFECT_BY_RESOURCE = {
    "ram": "scratch",
    "disk": "durable-internal",
    "s3": "durable-internal",
    "redis": "durable-internal",
    "notion": "durable-internal",
    "postgres": "system-of-record",
    "mongodb": "system-of-record",
    "slack": "external-effect",
    "linear": "external-effect",
    "gmail": "external-effect",
    "github": "external-effect",
    "github_ci": "external-effect",
    "discord": "external-effect",
    "telegram": "external-effect",
    "trello": "external-effect",
}
_REVERSIBILITY = {
    "scratch": "Ephemeral scratch — discarded on reset.",
    "durable-internal": "Soft/reversible on most object stores.",
    "system-of-record": "Consistency-sensitive — review before promoting.",
    "external-effect": "Irreversible once sent — cannot be unsent.",
}


@dataclass
class ConsoleMount:
    prefix: str
    resource: str
    mode: str
    effect_class: str
    description: str = ""


@dataclass
class ConsoleWorkspace:
    id: str
    name: str
    template_id: str
    mounts: list[ConsoleMount]
    mount_specs: list[dict]
    mode: str = "TEST"
    branch: str = "main"
    parent_id: str | None = None
    workspace: object = field(default=None, repr=False)
    pinned_backing: str | None = None
    status: str = "created"
    created_at: float = 0.0
    promoted_keys: set = field(default_factory=set)
    snapshots: list[dict] = field(default_factory=list)
    error: str | None = None


_console_workspaces: dict[str, ConsoleWorkspace] = {}


def _console_row(cws: ConsoleWorkspace) -> dict:
    return {
        "id": cws.id,
        "name": cws.name,
        "template_id": cws.template_id,
        "mode": cws.mode,
        "branch": cws.branch,
        "parent_id": cws.parent_id,
        "pinned_backing": cws.pinned_backing,
        "status": cws.status,
        "error": cws.error,
        "created_at": cws.created_at,
        "mount_specs": cws.mount_specs,
        "mounts": [asdict(m) for m in cws.mounts],
        "promoted_keys": sorted(cws.promoted_keys),
        "snapshots": cws.snapshots,
        "effects_cache": getattr(cws, "_effects_cache", None),
        "overlay_cache": getattr(cws, "_overlay_cache", None),
        "trajectory_cache": getattr(cws, "_trajectory_cache", None),
    }


async def _persist_console(cws: ConsoleWorkspace) -> None:
    if _store is not None:
        await _store.upsert_console_workspace(_console_row(cws))


def _restore_console_workspace(row: dict) -> None:
    cws = ConsoleWorkspace(
        id=row["id"],
        name=row["name"],
        template_id=row["template_id"],
        mounts=[ConsoleMount(**m) for m in (row.get("mounts") or [])],
        mount_specs=row.get("mount_specs") or [],
        mode=row.get("mode", "TEST"),
        branch=row.get("branch", "main"),
        parent_id=row.get("parent_id"),
        pinned_backing=row.get("pinned_backing"),
        status=row.get("status", "ready"),
        created_at=row.get("created_at", 0.0),
        promoted_keys=set(row.get("promoted_keys") or []),
        snapshots=row.get("snapshots") or [],
        error=row.get("error"),
    )
    cws._effects_cache = row.get("effects_cache")
    cws._overlay_cache = row.get("overlay_cache")
    cws._trajectory_cache = row.get("trajectory_cache")
    _console_workspaces[cws.id] = cws


async def _ensure_console_live(cws: ConsoleWorkspace):
    if cws.workspace is not None:
        return cws.workspace
    if cws.status == "created":
        return None
    ws = _build_console_workspace(cws.mount_specs)
    if ws is None:
        cws.status = "error"
        cws.error = ("workspace could not be rebuilt after restart — "
                     "overlay writes since the last snapshot are lost")
        await _persist_console(cws)
        return None
    cws.workspace = ws
    if cws.status == "error":
        cws.status = "ready"
        cws.error = None
    return ws


def _norm_prefix(prefix: str) -> str:
    return prefix.rstrip("/") or "/"


def _effect_class_for_mount(prefix: str, resource: str) -> str:
    head = prefix.strip("/").split("/")[0].lower()
    if not head:
        return "scratch"
    if head in _EFFECT_BY_PREFIX:
        return _EFFECT_BY_PREFIX[head]
    return _EFFECT_BY_RESOURCE.get(resource, "durable-internal")


async def _safe_json(request: Request) -> dict:
    raw = await request.body()
    if not raw:
        return {}
    data = json.loads(raw)
    return data if isinstance(data, dict) else {}


async def _console_emit(event: dict) -> None:
    await _persist_and_broadcast(event)


def _build_console_workspace(mount_specs: list[dict]):
    _ensure_fixture_disk()
    if not _HAS_MIRAGE:
        return None
    mounts: dict[str, tuple] = {"/": (RAMResource(), MountMode.WRITE)}
    for spec in mount_specs:
        path = str(spec.get("path", "")).rstrip("/")
        if not path or path == "/":
            continue
        mode = MountMode.WRITE if spec.get("mode") == "rw" else MountMode.READ
        head = path.strip("/").split("/")[0]
        disk_dir = DISK_ROOT / head
        if disk_dir.exists() and disk_dir.is_dir():
            mounts[f"/{head}"] = (DiskResource(root=str(disk_dir)), mode)
        else:
            mounts[path] = (RAMResource(), MountMode.WRITE)
    if len(mounts) <= 1 and not mount_specs:
        return None
    return Workspace(mounts, mode=MountMode.WRITE)


def _console_user_mounts(ws) -> list:
    out = []
    for m in ws.mounts():
        prefix = m.prefix
        if prefix in ("/dev/", "/dev") or prefix.startswith("/."):
            continue
        out.append(m)
    return out


def _console_mounts_detail(cws: ConsoleWorkspace) -> list[dict]:
    ws = cws.workspace
    if ws is None:
        return [{
            "prefix":
            s.get("path", ""),
            "resource":
            "pending",
            "mode":
            s.get("mode", "ro"),
            "effect_class":
            _effect_class_for_mount(s.get("path", ""), "disk"),
        } for s in cws.mount_specs]
    result = []
    for m in _console_user_mounts(ws):
        resource = getattr(m.resource, "name", "ram")
        mode = getattr(getattr(m, "mode", None), "value", "read")
        prefix = _norm_prefix(m.prefix)
        result.append({
            "prefix":
            prefix,
            "resource":
            resource,
            "mode":
            mode,
            "effect_class":
            _effect_class_for_mount(prefix, resource),
        })
    return result


def _console_effects(cws: ConsoleWorkspace) -> list[dict]:
    ws = cws.workspace
    if ws is None:
        return getattr(cws, "_effects_cache", None) or []
    effect_for_prefix = {
        m["prefix"]: m["effect_class"]
        for m in _console_mounts_detail(cws)
    }
    effects = []
    records = getattr(ws.ops, "records", None) or []
    for idx, rec in enumerate(records):
        if rec.op not in _WRITE_OP_NAMES:
            continue
        prefix = _norm_prefix(rec.mount_prefix or "/")
        effect_class = effect_for_prefix.get(
            prefix) or _effect_class_for_mount(prefix, rec.source)
        key = f"{idx}:{rec.op}:{rec.path}"
        promoted = key in cws.promoted_keys
        if promoted:
            capture_state = "live"
        elif effect_class == "external-effect":
            capture_state = "simulated"
        else:
            capture_state = "captured"
        effects.append({
            "key": key,
            "op": rec.op,
            "path": rec.path,
            "mount_prefix": prefix,
            "source": rec.source,
            "bytes": rec.bytes,
            "effect_class": effect_class,
            "capture_state": capture_state,
            "target": rec.path,
            "reversibility": _REVERSIBILITY.get(effect_class, ""),
            "promoted": promoted,
            "timestamp": rec.timestamp,
        })
    return effects


def _console_pending_count(cws: ConsoleWorkspace) -> int:
    return sum(1 for e in _console_effects(cws) if not e["promoted"])


def _console_overlay(cws: ConsoleWorkspace) -> dict:
    ws = cws.workspace
    if ws is None:
        cached = getattr(cws, "_overlay_cache", None)
        if cached is not None:
            return cached
    per_mount: dict[str, dict] = {}
    for m in _console_mounts_detail(cws):
        per_mount[m["prefix"]] = {
            "prefix": m["prefix"],
            "resource": m["resource"],
            "mode": m["mode"],
            "effect_class": m["effect_class"],
            "changes": [],
        }
    if ws is not None:
        records = getattr(ws.ops, "records", None) or []
        for idx, rec in enumerate(records):
            if rec.op not in _WRITE_OP_NAMES:
                continue
            prefix = _norm_prefix(rec.mount_prefix or "/")
            bucket = per_mount.get(prefix)
            if bucket is None:
                bucket = {
                    "prefix": prefix,
                    "resource": rec.source,
                    "mode": "write",
                    "effect_class":
                    _effect_class_for_mount(prefix, rec.source),
                    "changes": [],
                }
                per_mount[prefix] = bucket
            bucket["changes"].append({
                "key": f"{idx}:{rec.op}:{rec.path}",
                "op": rec.op,
                "path": rec.path,
                "bytes": rec.bytes,
                "timestamp": rec.timestamp,
            })
    return {"mounts": list(per_mount.values())}


def _console_trajectory(cws: ConsoleWorkspace) -> list[dict]:
    ws = cws.workspace
    if ws is None:
        return getattr(cws, "_trajectory_cache", None) or []
    effect_for_prefix = {
        m["prefix"]: m["effect_class"]
        for m in _console_mounts_detail(cws)
    }
    entries = []
    records = getattr(ws.ops, "records", None) or []
    for idx, rec in enumerate(records):
        prefix = _norm_prefix(rec.mount_prefix or "/")
        effect_class = effect_for_prefix.get(
            prefix) or _effect_class_for_mount(prefix, rec.source)
        if rec.op in _WRITE_OP_NAMES:
            kind = "write"
            key = f"{idx}:{rec.op}:{rec.path}"
            if key in cws.promoted_keys:
                capture_state = "live"
            elif effect_class == "external-effect":
                capture_state = "simulated"
            else:
                capture_state = "captured"
        elif rec.op == "read":
            kind = "read"
            capture_state = None
        else:
            kind = "meta"
            capture_state = None
        entries.append({
            "idx": idx,
            "op": rec.op,
            "kind": kind,
            "path": rec.path,
            "mount_prefix": prefix,
            "source": rec.source,
            "bytes": rec.bytes,
            "duration_ms": rec.duration_ms,
            "timestamp": rec.timestamp,
            "effect_class": effect_class,
            "capture_state": capture_state,
        })
    return entries


def _test_step(cmd: str, output: str, exit_code: int, ops: list) -> dict:
    return {
        "command": cmd,
        "exit_code": exit_code,
        "stdout": output[:2000],
        "op_count": len(ops),
        "wrote": any(r.op in _WRITE_OP_NAMES for r in ops),
        "ok": exit_code == 0,
    }


async def _console_test_run(cws: ConsoleWorkspace,
                            commands: list[str] | None) -> dict:
    ws = cws.workspace
    steps: list[dict] = []
    permissions: list[dict] = []
    if commands:
        for cmd in commands:
            output, code, ops = await _execute_in_workspace_detailed(
                ws, cmd, cws.id)
            steps.append(_test_step(cmd, output, code, ops))
        ok = all(s["ok"] for s in steps)
    else:
        output, code, ops = await _execute_in_workspace_detailed(
            ws, "ls -la /", cws.id)
        steps.append(_test_step("ls -la /", output, code, ops))
        for m in _console_mounts_detail(cws):
            prefix = m["prefix"].rstrip("/")
            if not prefix:
                continue
            probe = f"{prefix}/.mirage_test_probe"
            cmd = f'echo "mirage-test-probe-{cws.id}" > {probe}'
            output, code, ops = await _execute_in_workspace_detailed(
                ws, cmd, cws.id)
            steps.append(_test_step(cmd, output, code, ops))
            wrote = any(r.op in _WRITE_OP_NAMES for r in ops)
            if wrote:
                read_cmd = f"cat {probe}"
                r_out, r_code, r_ops = await _execute_in_workspace_detailed(
                    ws, read_cmd, cws.id)
                steps.append(_test_step(read_cmd, r_out, r_code, r_ops))
            expected = m["mode"] == "write"
            permissions.append({
                "prefix": m["prefix"],
                "mode": m["mode"],
                "effect_class": m["effect_class"],
                "writable": wrote,
                "expected_writable": expected,
                "enforced": wrote == expected,
            })
        ok = steps[0]["ok"] and all(p["enforced"] for p in permissions)
    return {
        "workspace_id": cws.id,
        "ok": ok,
        "steps": steps,
        "permissions": permissions,
        "captured_writes": _console_pending_count(cws),
    }


def _console_brief(cws: ConsoleWorkspace) -> dict:
    return {
        "id": cws.id,
        "name": cws.name,
        "template_id": cws.template_id,
        "mode": cws.mode,
        "branch": cws.branch,
        "parent_id": cws.parent_id,
        "status": cws.status,
        "mount_count": len(cws.mount_specs),
        "pending_effects": _console_pending_count(cws),
        "created_at": cws.created_at,
    }


def _console_detail(cws: ConsoleWorkspace) -> dict:
    d = _console_brief(cws)
    d["mounts"] = _console_mounts_detail(cws)
    d["snapshots"] = cws.snapshots
    d["pinned_backing"] = bool(cws.pinned_backing)
    d["error"] = cws.error
    return d


@app.get("/api/console/workspaces")
async def console_list_workspaces() -> list[dict]:
    return [
        _console_brief(c) for c in sorted(
            _console_workspaces.values(),
            key=lambda x: x.created_at,
            reverse=True,
        )
    ]


@app.post("/api/console/workspaces")
async def console_create_workspace(request: Request) -> dict:
    body = await _safe_json(request)
    ws_id = str(uuid.uuid4())[:8]
    template_id = body.get("template_id", "custom")
    name = body.get("name") or f"workspace-{ws_id}"
    mount_specs = body.get("mounts") or [{"path": "/scratch", "mode": "rw"}]
    mounts_meta = [
        ConsoleMount(
            prefix=s.get("path", ""),
            resource="disk",
            mode=s.get("mode", "ro"),
            effect_class=_effect_class_for_mount(s.get("path", ""), "disk"),
        ) for s in mount_specs
    ]
    cws = ConsoleWorkspace(
        id=ws_id,
        name=name,
        template_id=template_id,
        mounts=mounts_meta,
        mount_specs=mount_specs,
        created_at=time.time(),
    )
    _console_workspaces[ws_id] = cws
    await _persist_console(cws)
    return _console_detail(cws)


@app.get("/api/console/workspaces/{ws_id}")
async def console_get_workspace(ws_id: str):
    cws = _console_workspaces.get(ws_id)
    if not cws:
        return JSONResponse({"error": "not found"}, status_code=404)
    return _console_detail(cws)


@app.delete("/api/console/workspaces/{ws_id}")
async def console_delete_workspace(ws_id: str):
    cws = _console_workspaces.pop(ws_id, None)
    if not cws:
        return JSONResponse({"error": "not found"}, status_code=404)
    if cws.workspace is not None:
        try:
            await cws.workspace.close()
        except Exception as exc:
            logger.warning("console workspace close failed: %s", exc)
    if _store is not None:
        await _store.delete_console_workspace(ws_id)
    return {"id": ws_id, "closed_at": time.time()}


@app.post("/api/console/workspaces/{ws_id}/standup/dryrun")
async def console_standup_dryrun(ws_id: str):
    cws = _console_workspaces.get(ws_id)
    if not cws:
        return JSONResponse({"error": "not found"}, status_code=404)
    projected = []
    total_bytes = 0
    total_files = 0
    for spec in cws.mount_specs:
        path = str(spec.get("path", ""))
        head = path.strip("/").split("/")[0]
        disk_dir = DISK_ROOT / head
        size = 0
        files = 0
        if disk_dir.exists() and disk_dir.is_dir():
            for f in disk_dir.rglob("*"):
                if f.is_file():
                    size += f.stat().st_size
                    files += 1
        total_bytes += size
        total_files += files
        projected.append({
            "path": path,
            "mode": spec.get("mode", "ro"),
            "effect_class": _effect_class_for_mount(path, "disk"),
            "exists": disk_dir.exists(),
            "bytes": size,
            "files": files,
        })
    return {
        "workspace_id":
        ws_id,
        "mounts":
        projected,
        "estimated_snapshot_bytes":
        total_bytes,
        "estimated_files":
        total_files,
        "cache_plan":
        "Pin backing snapshot of read-only mounts; RAM overlay captures writes.",
    }


@app.post("/api/console/workspaces/{ws_id}/standup")
async def console_standup(ws_id: str):
    cws = _console_workspaces.get(ws_id)
    if not cws:
        return JSONResponse({"error": "not found"}, status_code=404)
    ws = _build_console_workspace(cws.mount_specs)
    if ws is None:
        cws.status = "error"
        cws.error = "workspace unavailable (mirage or fixture disk missing)"
        return JSONResponse({"error": cws.error}, status_code=400)
    cws.workspace = ws
    cws.error = None
    try:
        _CONSOLE_SNAP_DIR.mkdir(parents=True, exist_ok=True)
        snap_path = str(_CONSOLE_SNAP_DIR / f"{ws_id}-backing.tar")
        await ws.snapshot(snap_path)
        cws.pinned_backing = snap_path
    except Exception as exc:
        logger.warning("console standup snapshot failed: %s", exc)
        cws.pinned_backing = None
    cws.status = "ready"
    await _persist_console(cws)
    await _console_emit({
        "type": "console_standup",
        "workspace_id": ws_id,
        "status": "ready",
    })
    return _console_detail(cws)


@app.post("/api/console/workspaces/{ws_id}/branch")
async def console_branch(ws_id: str, request: Request):
    cws = _console_workspaces.get(ws_id)
    if not cws:
        return JSONResponse({"error": "not found"}, status_code=404)
    if await _ensure_console_live(cws) is None:
        return JSONResponse({"error": "stand up the workspace first"},
                            status_code=400)
    body = await _safe_json(request)
    new_id = str(uuid.uuid4())[:8]
    try:
        new_ws = await cws.workspace.copy()
    except Exception as exc:
        logger.warning("console branch failed: %s", exc)
        return JSONResponse({"error": f"branch failed: {exc}"},
                            status_code=500)
    branch_name = body.get("branch") or f"branch-{new_id}"
    child = ConsoleWorkspace(
        id=new_id,
        name=f"{cws.name} · {branch_name}",
        template_id=cws.template_id,
        mounts=list(cws.mounts),
        mount_specs=list(cws.mount_specs),
        mode=cws.mode,
        branch=branch_name,
        parent_id=cws.id,
        workspace=new_ws,
        pinned_backing=cws.pinned_backing,
        status="ready",
        created_at=time.time(),
        promoted_keys=set(cws.promoted_keys),
    )
    _console_workspaces[new_id] = child
    await _persist_console(child)
    await _console_emit({
        "type": "console_branch",
        "workspace_id": new_id,
        "parent_id": cws.id,
        "branch": branch_name,
    })
    return _console_detail(child)


@app.post("/api/console/workspaces/{ws_id}/snapshot")
async def console_snapshot(ws_id: str, request: Request):
    cws = _console_workspaces.get(ws_id)
    if not cws:
        return JSONResponse({"error": "not found"}, status_code=404)
    if await _ensure_console_live(cws) is None:
        return JSONResponse({"error": "stand up the workspace first"},
                            status_code=400)
    body = await _safe_json(request)
    name = body.get("name") or f"snap-{len(cws.snapshots) + 1}"
    _CONSOLE_SNAP_DIR.mkdir(parents=True, exist_ok=True)
    path = str(_CONSOLE_SNAP_DIR / f"{ws_id}-{name}.tar")
    await cws.workspace.snapshot(path)
    size = Path(path).stat().st_size if Path(path).exists() else 0
    entry = {
        "name": name,
        "path": path,
        "size": size,
        "created_at": time.time(),
    }
    cws.snapshots.append(entry)
    await _persist_console(cws)
    return entry


@app.post("/api/console/workspaces/{ws_id}/reset")
async def console_reset(ws_id: str):
    cws = _console_workspaces.get(ws_id)
    if not cws:
        return JSONResponse({"error": "not found"}, status_code=404)
    new_ws = _build_console_workspace(cws.mount_specs)
    if new_ws is None:
        return JSONResponse({"error": "workspace unavailable"},
                            status_code=400)
    old = cws.workspace
    cws.workspace = new_ws
    cws.promoted_keys = set()
    for s in _sessions.values():
        if s.workspace is old:
            s.workspace = new_ws
    if old is not None:
        try:
            await old.close()
        except Exception as exc:
            logger.warning("console reset close failed: %s", exc)
    cws.status = "ready"
    cws.error = None
    await _persist_console(cws)
    await _console_emit({"type": "console_reset", "workspace_id": ws_id})
    return _console_detail(cws)


@app.get("/api/console/workspaces/{ws_id}/overlay")
async def console_get_overlay(ws_id: str):
    cws = _console_workspaces.get(ws_id)
    if not cws:
        return JSONResponse({"error": "not found"}, status_code=404)
    data = _console_overlay(cws)
    if cws.workspace is not None:
        cws._overlay_cache = data
        await _persist_console(cws)
    return data


@app.get("/api/console/workspaces/{ws_id}/effects")
async def console_get_effects(ws_id: str):
    cws = _console_workspaces.get(ws_id)
    if not cws:
        return JSONResponse({"error": "not found"}, status_code=404)
    data = _console_effects(cws)
    if cws.workspace is not None:
        cws._effects_cache = data
        await _persist_console(cws)
    return {"effects": data}


@app.get("/api/console/workspaces/{ws_id}/trajectory")
async def console_get_trajectory(ws_id: str):
    cws = _console_workspaces.get(ws_id)
    if not cws:
        return JSONResponse({"error": "not found"}, status_code=404)
    data = _console_trajectory(cws)
    if cws.workspace is not None:
        cws._trajectory_cache = data
        await _persist_console(cws)
    return {"entries": data}


@app.post("/api/console/workspaces/{ws_id}/test-run")
async def console_test_run(ws_id: str, request: Request):
    cws = _console_workspaces.get(ws_id)
    if not cws:
        return JSONResponse({"error": "not found"}, status_code=404)
    if await _ensure_console_live(cws) is None:
        return JSONResponse({"error": "stand up the workspace first"},
                            status_code=400)
    body = await _safe_json(request)
    commands = body.get("commands")
    if commands is not None and not isinstance(commands, list):
        return JSONResponse({"error": "commands must be a list of strings"},
                            status_code=400)
    await _console_emit({
        "type": "console_test_run",
        "workspace_id": ws_id,
        "status": "started",
    })
    result = await _console_test_run(cws, commands)
    await _console_emit({
        "type": "console_test_run",
        "workspace_id": ws_id,
        "status": "finished",
        "ok": result["ok"],
    })
    return result


@app.post("/api/console/workspaces/{ws_id}/promote")
async def console_promote(ws_id: str, request: Request):
    cws = _console_workspaces.get(ws_id)
    if not cws:
        return JSONResponse({"error": "not found"}, status_code=404)
    body = await _safe_json(request)
    keys = body.get("keys") or []
    effects = {e["key"]: e for e in _console_effects(cws)}
    results = []
    for k in keys:
        e = effects.get(k)
        if e is None:
            results.append({"key": k, "status": "missing"})
            continue
        cws.promoted_keys.add(k)
        results.append({
            "key": k,
            "status": "promoted",
            "effect_class": e["effect_class"],
            "simulated": True,
        })
        await _console_emit({
            "type": "console_promote",
            "workspace_id": ws_id,
            "key": k,
            "effect_class": e["effect_class"],
            "path": e["path"],
            "simulated": True,
        })
    await _persist_console(cws)
    return {
        "results": results,
        "promoted_total": len(cws.promoted_keys),
        "pending": _console_pending_count(cws),
        "simulated": True,
    }


@app.post("/api/console/workspaces/{ws_id}/mode")
async def console_set_mode(ws_id: str, request: Request):
    cws = _console_workspaces.get(ws_id)
    if not cws:
        return JSONResponse({"error": "not found"}, status_code=404)
    body = await _safe_json(request)
    mode = str(body.get("mode", "TEST")).upper()
    if mode not in ("TEST", "LIVE"):
        return JSONResponse({"error": "mode must be TEST or LIVE"},
                            status_code=400)
    cws.mode = mode
    await _persist_console(cws)
    await _console_emit({
        "type": "console_mode",
        "workspace_id": ws_id,
        "mode": mode,
    })
    return _console_detail(cws)


@app.get("/api/console/workspaces/{ws_id}/file")
async def console_file(ws_id: str, path: str = "/"):
    cws = _console_workspaces.get(ws_id)
    if not cws:
        return JSONResponse({"error": "not found"}, status_code=404)
    if await _ensure_console_live(cws) is None:
        return JSONResponse({"error": "stand up the workspace first"},
                            status_code=400)
    content = await _execute_in_workspace(cws.workspace, f"cat {path}", ws_id)
    return {"content": content, "size": len(content), "path": path}


@app.post("/api/console/workspaces/{ws_id}/session")
async def console_create_session(ws_id: str, request: Request):
    cws = _console_workspaces.get(ws_id)
    if not cws:
        return JSONResponse({"error": "not found"}, status_code=404)
    if await _ensure_console_live(cws) is None:
        return JSONResponse({"error": "stand up the workspace first"},
                            status_code=400)
    await _safe_json(request)
    session_id = str(uuid.uuid4())[:8]
    session = AgentSession(
        id=session_id,
        services=[],
        created_at=time.time(),
        workspace=cws.workspace,
        kind="console",
    )
    _sessions[session_id] = session
    _persist_session(session)
    return {
        "id": session_id,
        "workspace_id": ws_id,
        "status": session.status,
        "has_workspace": True,
    }


# ── Health ─────────────────────────────────────────────────────────────


@app.get("/api/health")
async def health() -> dict:
    disk_subdirs = []
    if DISK_ROOT.exists():
        disk_subdirs = sorted(d.name for d in DISK_ROOT.iterdir()
                              if d.is_dir())
    workspace_ready = _build_workspace([]) is not None
    return {
        "status": "ok",
        "disk_root": str(DISK_ROOT),
        "disk_exists": DISK_ROOT.exists(),
        "disk_subdirs": disk_subdirs,
        "has_mirage": _HAS_MIRAGE,
        "has_eval_package": build_l1_workspace is not None,
        "workspace_ready": workspace_ready,
        "traces_db": TRACES_DB or None,
        "events_buffered": len(_event_buffer),
        "sessions": len(_sessions),
        "has_api_key": bool(OPENAI_API_KEY),
        "persistence": _store.dialect if _store is not None else None,
    }


# ── Static files ───────────────────────────────────────────────────────

dist_dir = Path(__file__).parent / "dist"
if dist_dir.exists():
    app.mount("/",
              StaticFiles(directory=str(dist_dir), html=True),
              name="static")

if __name__ == "__main__":
    reload = os.environ.get("RELOAD", "").lower() in ("1", "true", "yes")
    platform_dir = Path(__file__).parent
    port = int(os.environ.get("PORT", "8080"))
    if reload:
        uvicorn.run(
            "server:app",
            host="0.0.0.0",
            port=port,
            reload=True,
            app_dir=str(platform_dir),
            reload_dirs=[str(platform_dir)],
        )
    else:
        uvicorn.run(app, host="0.0.0.0", port=port)
