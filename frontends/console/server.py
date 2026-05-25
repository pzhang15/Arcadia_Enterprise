import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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

app = FastAPI(title="Mirage Agent Console")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

RELAY_URL = os.environ.get("RELAY_URL", "http://localhost:8082")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL",
                                 "https://api.openai.com/v1")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")

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
_relay_client: httpx.AsyncClient | None = None
_openai_client = None


def _get_relay_client() -> httpx.AsyncClient:
    global _relay_client
    if _relay_client is None:
        _relay_client = httpx.AsyncClient(timeout=2.0)
    return _relay_client


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
    try:
        client = _get_relay_client()
        await client.post(f"{RELAY_URL}/ingest", json=event)
    except Exception:
        logger.debug("relay unreachable")


def _build_workspace(services: list[str]):
    """Build a Mirage workspace with mounts for the selected services."""
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
    """Build a dynamic file prompt based on selected services."""
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
    """Execute a command in the Mirage workspace and return stdout."""
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
    """Run one conversation turn: send user message to LLM, execute any
    commands the LLM requests, and return the final response."""
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
            "to enable the agent. For now, you can explore the data through "
            "the Enterprise Portal at http://localhost:8083.")
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
    }


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "sessions": len(_sessions),
        "has_api_key": bool(OPENAI_API_KEY),
        "openai_available": AsyncOpenAI is not None,
        "model": OPENAI_MODEL,
    }


dist_dir = Path(__file__).parent / "dist"
if dist_dir.exists():
    app.mount("/",
              StaticFiles(directory=str(dist_dir), html=True),
              name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8084)
