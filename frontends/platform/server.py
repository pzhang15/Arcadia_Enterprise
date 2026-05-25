import asyncio
import json
import logging
import os
import sqlite3
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

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

logger = logging.getLogger(__name__)

DISK_ROOT = Path(
    os.environ.get(
        "DISK_ROOT",
        str(
            Path(__file__).resolve().parent.parent / "packages" / "eval" /
            "scenarios" / "northhill_corp" / "fixture" / "disk"),
    ))
RESULTS_DIR = Path(
    os.environ.get(
        "RESULTS_DIR",
        str(Path(__file__).resolve().parent.parent / "packages" / "eval" /
            "results"),
    ))
TRACES_DB = os.environ.get("TRACES_DB", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL",
                                 "https://api.openai.com/v1")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")

app = FastAPI(title="Arcadia Platform")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── SSE Event Relay ────────────────────────────────────────────────────

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
or run additional commands as needed.\
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
    error: str | None = None


_sessions: dict[str, AgentSession] = {}
_openai_client = None


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
    _event_buffer.append(event)
    await _broadcast(event)


def _build_workspace(services: list[str]):
    if _seed_northhill is None or build_l1_workspace is None:
        logger.warning(
            "workspace modules not available (packages/eval not installed)")
        return None
    try:
        _seed_northhill()
        return build_l1_workspace(agent_id="console-agent",
                                  session_id="default")
    except Exception as exc:
        logger.warning("workspace build failed: %s", exc)
        return None


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


async def _execute_in_workspace(ws, command: str, session_id: str) -> str:
    try:
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
        for rec in (ws.ops.records or [])[-20:]:
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
                })
        output = stdout.rstrip()
        if stderr.strip():
            output += f"\n[stderr] {stderr.rstrip()}"
        if exit_code != 0:
            output += f"\n[exit_code={exit_code}]"
        return output or "(no output)"
    except Exception as exc:
        return f"[error] {type(exc).__name__}: {exc}"


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
                output = "(workspace not available — set OPENAI_API_KEY and seed data)"
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
        return {"reply": reply, "status": "ready"}
    reply = await _run_conversation_turn(session, user_message)
    return {"reply": reply, "status": session.status}


@app.get("/api/sessions/{session_id}/history")
async def session_history(session_id: str) -> list[dict]:
    session = _sessions.get(session_id)
    if not session:
        return JSONResponse({"error": "not found"}, status_code=404)
    return [{
        "role": e.role,
        "content": e.content,
        "timestamp": e.timestamp
    } for e in session.chat_history]


@app.get("/api/sessions/{session_id}/status")
async def session_status(session_id: str) -> dict:
    session = _sessions.get(session_id)
    if not session:
        return JSONResponse({"error": "not found"}, status_code=404)
    return {
        "id": session.id,
        "status": session.status,
        "services": session.services,
        "created_at": session.created_at,
        "message_count": len(session.chat_history),
        "error": session.error,
    }


@app.get("/api/sessions")
async def list_sessions() -> list[dict]:
    return [{
        "id":
        s.id,
        "status":
        s.status,
        "services":
        s.services,
        "created_at":
        s.created_at,
        "message_count":
        len(s.chat_history),
        "last_message":
        s.chat_history[-1].content[:100] if s.chat_history else "",
    } for s in sorted(
        _sessions.values(), key=lambda x: x.created_at, reverse=True)]


@app.get("/api/quick-actions")
async def quick_actions() -> list[dict]:
    return [
        {
            "id": "triage",
            "label": "Triage IT helpdesk queue",
            "services": ["it", "hr"],
            "task": "Triage all open IT helpdesk tickets. List each one with its priority, classify by severity, find any duplicates, and identify tickets needing escalation."
        },
        {
            "id": "onboarding",
            "label": "Check onboarding status",
            "services": ["it", "hr"],
            "task": "Look up Alex Rivera's onboarding status. Check the New Hire Tracker spreadsheet, any open IT tickets for Alex, and relevant Slack messages."
        },
        {
            "id": "incident",
            "label": "Investigate platform incident",
            "services": ["engineering"],
            "task": "Investigate the active platform-api incident. Check PagerDuty for triggered incidents, correlate with recent deployments, check Datadog logs for errors, and identify root cause."
        },
        {
            "id": "expenses",
            "label": "Review pending expenses",
            "services": ["finance"],
            "task": "Review all pending expense reports. List each with submitter, amount, category, and flag any that exceed policy limits or are missing details. Summarize totals by department."
        },
        {
            "id": "escalations",
            "label": "Handle customer escalations",
            "services": ["support", "engineering"],
            "task": "Review active customer escalations and at-risk accounts. Check account health scores, open support tickets, and cross-reference with any engineering incidents that may be affecting customers."
        },
        {
            "id": "audit",
            "label": "SOC2 audit status",
            "services": ["compliance"],
            "task": "Check the SOC2 audit progress. List all checklist items with their completion status, identify blockers, and check policy acknowledgment rates."
        },
        {
            "id": "full",
            "label": "Full enterprise review",
            "services": ["it", "hr", "finance", "engineering", "support", "compliance"],
            "task": "Do a comprehensive cross-department review. Check IT tickets, onboarding status, pending expenses, active incidents, customer health, and compliance audit progress. Give me an executive summary."
        },
    ]


@app.get("/api/config")
async def get_config() -> dict:
    return {
        "has_api_key": bool(OPENAI_API_KEY),
        "openai_available": AsyncOpenAI is not None,
        "model": OPENAI_MODEL,
    }


# ── Health ─────────────────────────────────────────────────────────────


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "disk_root": str(DISK_ROOT),
        "disk_exists": DISK_ROOT.exists(),
        "traces_db": TRACES_DB or None,
        "events_buffered": len(_event_buffer),
        "sessions": len(_sessions),
        "has_api_key": bool(OPENAI_API_KEY),
    }


# ── Static files ───────────────────────────────────────────────────────

dist_dir = Path(__file__).parent / "dist"
if dist_dir.exists():
    app.mount("/",
              StaticFiles(directory=str(dist_dir), html=True),
              name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
