import asyncio
import json
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
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

app = FastAPI(title="Mirage Agent Console")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

RELAY_URL = os.environ.get("RELAY_URL", "http://localhost:8082")
SCENARIO_ROOT = Path(
    os.environ.get(
        "SCENARIO_ROOT",
        str(
            Path(__file__).resolve().parent.parent
            / "scenarios"
            / "acme_corp"
            / "fixture"
            / "disk"
        ),
    )
)


@dataclass
class AgentSession:
    id: str
    services: list[str]
    task: str = ""
    status: str = "created"
    created_at: float = 0.0
    completed_at: float | None = None
    result: dict = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)
    error: str | None = None


_sessions: dict[str, AgentSession] = {}
_relay_client: httpx.AsyncClient | None = None


def _get_relay_client() -> httpx.AsyncClient:
    global _relay_client
    if _relay_client is None:
        _relay_client = httpx.AsyncClient(timeout=2.0)
    return _relay_client


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


async def _run_agent(session: AgentSession) -> None:
    session.status = "running"
    await _emit_event(
        session.id,
        {
            "type": "agent_status",
            "status": "running",
            "task": session.task,
        },
    )

    commands_to_run = _plan_commands(session.services, session.task)

    files_created: dict[str, str] = {}
    services_touched: dict[str, int] = {}

    for cmd in commands_to_run:
        await asyncio.sleep(0.3)

        mount = "/" + cmd.split("/")[1] if "/" in cmd.split(" ")[-1] else "/"
        service = mount.strip("/").split("/")[0] if mount != "/" else "workspace"
        services_touched[service] = services_touched.get(service, 0) + 1

        stdout = _simulate_command_output(cmd, session.services)
        exit_code = 0

        await _emit_event(
            session.id,
            {
                "type": "command",
                "agent": "console-agent",
                "session": session.id,
                "command": cmd,
                "exit_code": exit_code,
                "stdout": stdout[:2000],
            },
        )

        if cmd.startswith("ls "):
            await _emit_event(
                session.id,
                {
                    "type": "op",
                    "agent": "console-agent",
                    "session": session.id,
                    "op": "readdir",
                    "path": cmd.split(" ", 1)[1],
                    "source": "disk",
                    "bytes": len(stdout.encode()),
                    "duration_ms": 2,
                    "mount_prefix": mount,
                },
            )
        elif cmd.startswith("cat "):
            await _emit_event(
                session.id,
                {
                    "type": "op",
                    "agent": "console-agent",
                    "session": session.id,
                    "op": "read",
                    "path": cmd.split(" ", 1)[1],
                    "source": "disk",
                    "bytes": len(stdout.encode()),
                    "duration_ms": 3,
                    "mount_prefix": mount,
                },
            )

    report_content = _generate_report(session.task, session.services, services_touched)
    files_created["/agent_report.md"] = report_content

    await _emit_event(
        session.id,
        {
            "type": "command",
            "agent": "console-agent",
            "session": session.id,
            "command": f"echo '{report_content[:100]}...' > /agent_report.md",
            "exit_code": 0,
            "stdout": "",
        },
    )

    session.status = "completed"
    session.completed_at = time.time()
    session.result = {
        "summary": report_content,
        "services_touched": services_touched,
        "files_created": files_created,
        "commands_run": len(commands_to_run),
        "duration_s": round(session.completed_at - session.created_at, 1),
    }

    await _emit_event(
        session.id,
        {
            "type": "agent_status",
            "status": "completed",
            "result": session.result,
        },
    )


def _plan_commands(services: list[str], task: str) -> list[str]:
    commands = ["ls /"]
    task_lower = task.lower()

    if (
        "it" in services
        or "helpdesk" in task_lower
        or "ticket" in task_lower
        or "triage" in task_lower
    ):
        commands.extend(
            [
                "ls /tickets/queues/it-helpdesk/",
                "ls /tickets/queues/it-helpdesk/open/",
                "cat /tickets/queues/it-helpdesk/open/INC-1001__laptop_not_arrived_for_alex.json",
                "cat /tickets/queues/it-helpdesk/open/INC-1002__aws_access_request_for_alex.json",
                "ls /tickets/queues/it-helpdesk/in_progress/",
            ]
        )

    if "hr" in services or "onboarding" in task_lower or "employee" in task_lower:
        commands.extend(
            [
                "ls /sheets/owned/",
                "cat /sheets/owned/2026-05-12_New_Hire_Tracker__SH101.gsheet.json",
                "ls /slack/channels/onboarding__C302/",
            ]
        )

    if "finance" in services or "expense" in task_lower or "budget" in task_lower:
        commands.extend(
            [
                "ls /finance/expenses/pending/",
                "cat /finance/budgets/Q2_2026.json",
                "ls /finance/purchase_orders/open/",
            ]
        )

    if "engineering" in services or "incident" in task_lower or "deploy" in task_lower:
        commands.extend(
            [
                "ls /pagerduty/incidents/triggered/",
                "ls /github/repos/acme-corp/platform-api/deployments/",
                "ls /datadog/logs/platform-api/",
            ]
        )

    if "support" in services or "customer" in task_lower or "escalat" in task_lower:
        commands.extend(
            [
                "ls /customers/accounts/",
                "ls /customers/escalations/",
                "ls /tickets/queues/customer-support/open/",
            ]
        )

    if (
        "compliance" in services
        or "audit" in task_lower
        or "soc2" in task_lower
        or "contract" in task_lower
    ):
        commands.extend(
            [
                "ls /compliance/audits/",
                "ls /compliance/contracts/in_review/",
                "ls /compliance/policies/",
            ]
        )

    return commands


def _simulate_command_output(cmd: str, services: list[str]) -> str:
    if cmd == "ls /":
        dirs = ["slack", "sheets", "gdocs", "tickets"]
        if "finance" in services:
            dirs.append("finance")
        if "engineering" in services:
            dirs.extend(["github", "pagerduty", "datadog"])
        if "support" in services:
            dirs.append("customers")
        if "compliance" in services:
            dirs.append("compliance")
        return "\n".join(sorted(dirs))

    if "tickets/queues/it-helpdesk/open" in cmd and cmd.startswith("ls"):
        return (
            "INC-1001__laptop_not_arrived_for_alex.json\n"
            "INC-1002__aws_access_request_for_alex.json\n"
            "INC-1004__github_org_invite_for_alex.json\n"
            "INC-1005__vpn_credentials_expired_for_bob.json\n"
            "INC-1006__slack_workspace_access_for_alex.json\n"
            "INC-1007__office_printer_jammed.json"
        )

    if "finance/expenses/pending" in cmd and cmd.startswith("ls"):
        return "EXP-1001.json\nEXP-1002.json\nEXP-1003.json\nEXP-1004.json\nEXP-1005.json\nEXP-1006.json"

    if "customers/accounts" in cmd and cmd.startswith("ls"):
        return "ACCT-1001.json\nACCT-1002.json\nACCT-1003.json\nACCT-1004.json\nACCT-1005.json\nACCT-1006.json"

    if "compliance/audits" in cmd and cmd.startswith("ls"):
        return "AUDIT-2026-SOC2.json\nAUDIT-2026-GDPR.json"

    if cmd.startswith("cat "):
        return '{"status": "loaded", "data": "..."}'

    if cmd.startswith("ls "):
        return "(directory listing)"

    return ""


def _generate_report(
    task: str, services: list[str], touched: dict[str, int]
) -> str:
    lines = ["# Agent Report", "", f"**Task:** {task}", ""]
    lines.append("## Services Accessed")
    for svc, count in sorted(touched.items()):
        lines.append(f"- **{svc}**: {count} operations")
    lines.append("")
    lines.append("## Findings")

    task_lower = task.lower()
    if "triage" in task_lower or "helpdesk" in task_lower:
        lines.extend(
            [
                "- 6 open IT helpdesk tickets found",
                "- INC-1001 (P2): Alex Rivera's laptop delayed - loaner assigned",
                "- INC-1003 (P2): Okta SSO provisioning in progress",
                "- INC-1006 is a near-duplicate of INC-1002 (recommend closing)",
                "- INC-1005 (P3): Bob Lee's VPN - open >48h, needs escalation",
            ]
        )
    if "expense" in task_lower or "finance" in task_lower:
        lines.extend(
            [
                "- 6 pending expense reports totaling ~$12,400",
                "- 2 reports flagged for missing receipts",
                "- Q2 budget utilization at 62% across departments",
            ]
        )
    if "incident" in task_lower or "engineering" in task_lower:
        lines.extend(
            [
                "- Active incident INC-5521: P99 latency spike on platform-api",
                "- Root cause: deployment d4e5f6 reduced connection pool from 50 to 10",
                "- Recommendation: rollback deployment or restore pool size",
            ]
        )
    if "customer" in task_lower or "escalat" in task_lower:
        lines.extend(
            [
                "- 3 active customer escalations",
                "- GlobalTech (ACCT-1001) at-risk: health score 45, login failures",
                "- PayRight data sync delay linked to engineering incident",
            ]
        )
    if "audit" in task_lower or "compliance" in task_lower:
        lines.extend(
            [
                "- SOC2 audit: 8/12 checklist items complete, due 2026-06-30",
                "- GDPR audit pending, 0/6 items started, due 2026-07-15",
                "- Policy acknowledgment rate: 75% across all policies",
            ]
        )
    if not any(
        kw in task_lower
        for kw in ["triage", "expense", "incident", "customer", "audit"]
    ):
        lines.extend(
            [
                "- Cross-department analysis completed",
                f"- Accessed {len(touched)} service areas",
                "- No critical blockers found",
            ]
        )

    lines.extend(["", "## Recommended Actions"])
    lines.append("1. Review findings above and take action on flagged items")
    lines.append("2. Schedule follow-up for any open escalations")
    lines.append("")
    return "\n".join(lines)


@app.post("/api/sessions")
async def create_session(request: Request) -> dict:
    body = await request.json()
    session_id = str(uuid.uuid4())[:8]
    session = AgentSession(
        id=session_id,
        services=body.get("services", []),
        created_at=time.time(),
    )
    _sessions[session_id] = session
    return {"id": session_id, "status": session.status, "services": session.services}


@app.post("/api/sessions/{session_id}/run")
async def run_session(session_id: str, request: Request) -> dict:
    session = _sessions.get(session_id)
    if not session:
        return JSONResponse({"error": "session not found"}, status_code=404)
    if session.status == "running":
        return JSONResponse({"error": "already running"}, status_code=409)
    body = await request.json()
    session.task = body.get("task", "")
    asyncio.create_task(_run_agent(session))
    return {"id": session_id, "status": "running", "task": session.task}


@app.get("/api/sessions/{session_id}/status")
async def session_status(session_id: str) -> dict:
    session = _sessions.get(session_id)
    if not session:
        return JSONResponse({"error": "not found"}, status_code=404)
    return {
        "id": session.id,
        "status": session.status,
        "task": session.task,
        "services": session.services,
        "created_at": session.created_at,
        "completed_at": session.completed_at,
        "error": session.error,
    }


@app.get("/api/sessions/{session_id}/result")
async def session_result(session_id: str) -> dict:
    session = _sessions.get(session_id)
    if not session:
        return JSONResponse({"error": "not found"}, status_code=404)
    return session.result


@app.get("/api/sessions")
async def list_sessions() -> list[dict]:
    return [
        {
            "id": s.id,
            "status": s.status,
            "task": s.task[:100],
            "services": s.services,
            "created_at": s.created_at,
            "completed_at": s.completed_at,
        }
        for s in sorted(_sessions.values(), key=lambda x: x.created_at, reverse=True)
    ]


@app.get("/api/quick-actions")
async def quick_actions() -> list[dict]:
    return [
        {
            "id": "triage",
            "label": "Triage IT helpdesk queue",
            "services": ["it", "hr"],
            "task": "Triage all open IT helpdesk tickets. Classify by priority, find duplicates, and identify any needing escalation.",
        },
        {
            "id": "onboarding",
            "label": "Check onboarding status",
            "services": ["it", "hr"],
            "task": "Look up Alex Rivera's onboarding status across HR tracker, IT tickets, and Slack messages.",
        },
        {
            "id": "incident",
            "label": "Investigate platform incident",
            "services": ["engineering"],
            "task": "Investigate the active platform-api incident. Check PagerDuty, deployments, logs, and Slack for root cause.",
        },
        {
            "id": "expenses",
            "label": "Review pending expenses",
            "services": ["finance"],
            "task": "Review all pending expense reports. Flag any missing receipts or policy violations. Summarize totals by department.",
        },
        {
            "id": "escalations",
            "label": "Handle customer escalations",
            "services": ["support", "engineering"],
            "task": "Review active customer escalations. Cross-reference with engineering incidents. Prioritize by account health and ARR.",
        },
        {
            "id": "audit",
            "label": "SOC2 audit status",
            "services": ["compliance", "it"],
            "task": "Check SOC2 audit progress. Identify incomplete checklist items, missing evidence, and policy acknowledgment gaps.",
        },
        {
            "id": "full",
            "label": "Full enterprise review",
            "services": [
                "it",
                "hr",
                "finance",
                "engineering",
                "support",
                "compliance",
            ],
            "task": "Comprehensive enterprise review: check IT tickets, onboarding, expenses, incidents, customer health, and compliance status. Produce an executive summary.",
        },
    ]


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "sessions": len(_sessions)}


dist_dir = Path(__file__).parent / "dist"
if dist_dir.exists():
    app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="static")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8084)
