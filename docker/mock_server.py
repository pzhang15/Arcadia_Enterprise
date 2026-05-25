import json
import logging
import os
import sys
import time
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent / "packages" / "eval"))

from scenarios.northhill_corp.seed import (CHANNEL_MESSAGES, CHANNELS, USERS,
                                          _slack_msg)

logger = logging.getLogger(__name__)

app = FastAPI(title="Mirage Mock Services")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_posted_messages: list[dict] = []
_ticket_comments: dict[str, list[dict]] = {}
_relay_url = os.environ.get("RELAY_URL", "http://localhost:8082")
_relay_client: httpx.AsyncClient | None = None


def _get_relay_client() -> httpx.AsyncClient:
    global _relay_client
    if _relay_client is None:
        _relay_client = httpx.AsyncClient(timeout=2.0)
    return _relay_client


def _derive_service(path: str) -> str:
    parts = path.strip("/").split("/")
    if parts:
        return parts[0]
    return "unknown"


class RequestLoggingMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ("/health", "/docs", "/openapi.json"):
            return await call_next(request)
        t0 = time.time()
        response = await call_next(request)
        duration_ms = int((time.time() - t0) * 1000)
        body_bytes = 0
        if hasattr(response, "body"):
            body_bytes = len(response.body)
        event = {
            "type": "mock_request",
            "timestamp": int(t0 * 1000),
            "service": _derive_service(request.url.path),
            "method": request.method,
            "path": request.url.path,
            "query": dict(request.query_params),
            "status_code": response.status_code,
            "response_bytes": body_bytes,
            "duration_ms": duration_ms,
        }
        try:
            client = _get_relay_client()
            await client.post(f"{_relay_url}/ingest", json=event)
        except Exception:
            logger.debug("relay unreachable, skipping event")
        return response


app.add_middleware(RequestLoggingMiddleware)


def _seed_tickets():
    import tempfile

    from scenarios.northhill_corp.seed import main as seed_main
    td = Path(tempfile.mkdtemp(prefix="mock-seed-"))
    seed_main(td, clean=True)
    tickets: dict[str, dict] = {}
    for queue_dir in (td / "tickets" / "queues").iterdir():
        if not queue_dir.is_dir():
            continue
        for status_dir in queue_dir.iterdir():
            if not status_dir.is_dir():
                continue
            for f in status_dir.iterdir():
                if f.suffix == ".json":
                    t = json.loads(f.read_text())
                    tickets[t["ticket_id"]] = t
    return tickets


def _seed_github():
    import tempfile

    from scenarios.northhill_corp.seed import main as seed_main
    td = Path(tempfile.mkdtemp(prefix="mock-seed-"))
    seed_main(td, clean=True)
    gh = td / "github" / "repos" / "northhill" / "platform-api"
    deployments = [
        json.loads(f.read_text())
        for f in sorted((gh / "deployments").glob("*.json"))
    ]
    commits = {
        f.stem: json.loads(f.read_text())
        for f in (gh / "commits").glob("*.json")
    }
    pulls = [
        json.loads(f.read_text())
        for f in sorted((gh / "pulls").glob("*.json"))
    ]
    return deployments, commits, pulls


def _seed_pagerduty():
    import tempfile

    from scenarios.northhill_corp.seed import main as seed_main
    td = Path(tempfile.mkdtemp(prefix="mock-seed-"))
    seed_main(td, clean=True)
    pd = td / "pagerduty"
    services = [
        json.loads(f.read_text())
        for f in sorted((pd / "services").glob("*.json"))
    ]
    incidents = []
    for status in ("triggered", "acknowledged", "resolved"):
        d = pd / "incidents" / status
        if d.exists():
            for f in sorted(d.glob("*.json")):
                incidents.append(json.loads(f.read_text()))
    return services, incidents


def _seed_datadog():
    import tempfile

    from scenarios.northhill_corp.seed import main as seed_main
    td = Path(tempfile.mkdtemp(prefix="mock-seed-"))
    seed_main(td, clean=True)
    dd = td / "datadog"
    logs = []
    for f in sorted((dd / "logs" / "payments-api").glob("*.jsonl")):
        for line in f.read_text().splitlines():
            if line.strip():
                logs.append(json.loads(line))
    metrics = {}
    for f in sorted((dd / "metrics" / "payments-api").glob("*.json")):
        metrics[f.stem] = json.loads(f.read_text())
    return logs, metrics


def _seed_finance():
    import tempfile

    from scenarios.northhill_corp.seed import main as seed_main
    td = Path(tempfile.mkdtemp(prefix="mock-seed-"))
    seed_main(td, clean=True)
    fin = td / "finance"
    expenses = []
    for status in ("pending", "approved", "rejected"):
        d = fin / "expenses" / status
        if d.exists():
            for f in sorted(d.glob("*.json")):
                expenses.append(json.loads(f.read_text()))
    purchase_orders = []
    for status in ("open", "approved", "received"):
        d = fin / "purchase_orders" / status
        if d.exists():
            for f in sorted(d.glob("*.json")):
                purchase_orders.append(json.loads(f.read_text()))
    invoices = []
    for status in ("pending", "paid", "disputed"):
        d = fin / "invoices" / status
        if d.exists():
            for f in sorted(d.glob("*.json")):
                invoices.append(json.loads(f.read_text()))
    budgets = {}
    budget_file = fin / "budgets" / "Q2_2026.json"
    if budget_file.exists():
        budgets = json.loads(budget_file.read_text())
    return expenses, purchase_orders, invoices, budgets


def _seed_customers():
    import tempfile

    from scenarios.northhill_corp.seed import main as seed_main
    td = Path(tempfile.mkdtemp(prefix="mock-seed-"))
    seed_main(td, clean=True)
    cust = td / "customers"
    accounts = []
    accts_dir = cust / "accounts"
    if accts_dir.exists():
        for f in sorted(accts_dir.glob("*.json")):
            accounts.append(json.loads(f.read_text()))
    escalations = []
    esc_dir = cust / "escalations"
    if esc_dir.exists():
        for f in sorted(esc_dir.glob("*.json")):
            escalations.append(json.loads(f.read_text()))
    return accounts, escalations


def _seed_compliance():
    import tempfile

    from scenarios.northhill_corp.seed import main as seed_main
    td = Path(tempfile.mkdtemp(prefix="mock-seed-"))
    seed_main(td, clean=True)
    comp = td / "compliance"
    contracts = []
    for status in ("in_review", "active", "expired"):
        d = comp / "contracts" / status
        if d.exists():
            for f in sorted(d.glob("*.json")):
                contracts.append(json.loads(f.read_text()))
    audits = []
    audits_dir = comp / "audits"
    if audits_dir.exists():
        for f in sorted(audits_dir.glob("*.json")):
            audits.append(json.loads(f.read_text()))
    policies = []
    policies_dir = comp / "policies"
    if policies_dir.exists():
        for f in sorted(policies_dir.glob("*.json")):
            policies.append(json.loads(f.read_text()))
    return contracts, audits, policies


TICKETS = _seed_tickets()
GH_DEPLOYMENTS, GH_COMMITS, GH_PULLS = _seed_github()
PD_SERVICES, PD_INCIDENTS = _seed_pagerduty()
DD_LOGS, DD_METRICS = _seed_datadog()

try:
    EXPENSES, PURCHASE_ORDERS, INVOICES, BUDGETS = _seed_finance()
    CUSTOMER_ACCOUNTS, ESCALATIONS = _seed_customers()
    CONTRACTS, AUDITS, POLICIES = _seed_compliance()
except Exception:
    EXPENSES, PURCHASE_ORDERS, INVOICES, BUDGETS = [], [], [], {}
    CUSTOMER_ACCOUNTS, ESCALATIONS = [], []
    CONTRACTS, AUDITS, POLICIES = [], [], []

# ── Slack Mock ──────────────────────────────────────────────────────────


@app.get("/slack/api/conversations.list")
async def slack_conversations_list():
    return {"ok": True, "channels": CHANNELS}


@app.get("/slack/api/conversations.history")
async def slack_conversations_history(
        channel: str = Query(...),
        oldest: str = Query(None),
        latest: str = Query(None),
        limit: int = Query(100),
):
    msgs = []
    for date, uid, ts, text in CHANNEL_MESSAGES.get(channel, []):
        msgs.append(_slack_msg(uid, ts, text))
    return {"ok": True, "messages": msgs, "has_more": False}


@app.post("/slack/api/chat.postMessage")
async def slack_post_message(request: Request):
    body = await request.json()
    _posted_messages.append(body)
    return {
        "ok": True,
        "channel": body.get("channel"),
        "ts": "1700000099.000100",
        "message": {
            "text": body.get("text", "")
        },
    }


@app.get("/slack/api/users.list")
async def slack_users_list():
    members = [{
        "id": u["id"],
        "name": u["handle"],
        "real_name": u["name"],
        "profile": {
            "title": u["title"],
            "email": u["email"]
        }
    } for u in USERS]
    return {"ok": True, "members": members}


# ── GitHub Mock ─────────────────────────────────────────────────────────


@app.get("/github/repos/{owner}/{repo}/deployments")
async def github_deployments(owner: str, repo: str):
    return GH_DEPLOYMENTS


@app.get("/github/repos/{owner}/{repo}/commits/{sha}")
async def github_commit(owner: str, repo: str, sha: str):
    commit = GH_COMMITS.get(sha)
    if not commit:
        return JSONResponse({"message": "Not Found"}, status_code=404)
    return commit


@app.get("/github/repos/{owner}/{repo}/pulls")
async def github_pulls(owner: str, repo: str):
    return GH_PULLS


# ── Jira Mock ───────────────────────────────────────────────────────────


@app.get("/jira/rest/api/2/search")
async def jira_search(jql: str = Query("")):
    results = list(TICKETS.values())
    if "status = open" in jql.lower():
        results = [t for t in results if t["status"] == "open"]
    if "status = resolved" in jql.lower():
        results = [t for t in results if t["status"] == "resolved"]
    project = None
    if "project = " in jql.lower():
        for part in jql.split():
            if part in ("OPS", "PAY", "ops", "pay"):
                project = part.upper()
        if project:
            results = [
                t for t in results if t.get("project", "").upper() == project
            ]
    return {"issues": results, "total": len(results)}


@app.get("/jira/rest/api/2/issue/{key}")
async def jira_issue(key: str):
    ticket = TICKETS.get(key)
    if not ticket:
        return JSONResponse({"errorMessages": ["Issue not found"]},
                            status_code=404)
    t = dict(ticket)
    t["comments"] = t.get("comments", []) + _ticket_comments.get(key, [])
    return t


@app.post("/jira/rest/api/2/issue/{key}/comment")
async def jira_add_comment(key: str, request: Request):
    if key not in TICKETS:
        return JSONResponse({"errorMessages": ["Issue not found"]},
                            status_code=404)
    body = await request.json()
    comment = {
        "author": body.get("author", "agent"),
        "body": body.get("body", ""),
        "created": "2026-05-15T15:00:00Z"
    }
    _ticket_comments.setdefault(key, []).append(comment)
    return comment


@app.get("/jira/rest/api/2/project")
async def jira_projects():
    return [{
        "key": "OPS",
        "name": "Operations"
    }, {
        "key": "PAY",
        "name": "Payments"
    }]


# ── PagerDuty Mock ──────────────────────────────────────────────────────


@app.get("/pagerduty/incidents")
async def pd_incidents(statuses: list[str] = Query(None,
                                                   alias="statuses[]"), ):
    results = PD_INCIDENTS
    if statuses:
        results = [i for i in results if i["status"] in statuses]
    return {"incidents": results}


@app.get("/pagerduty/incidents/{incident_id}")
async def pd_incident(incident_id: str):
    for inc in PD_INCIDENTS:
        if inc["id"] == incident_id:
            return {"incident": inc}
    return JSONResponse({"error": "Not Found"}, status_code=404)


@app.get("/pagerduty/services")
async def pd_services():
    return {"services": PD_SERVICES}


# ── Datadog Mock ────────────────────────────────────────────────────────


@app.post("/datadog/api/v1/logs/search")
async def dd_logs_search(request: Request):
    body = await request.json()
    query = body.get("filter", {}).get("query", "")
    results = DD_LOGS
    if query:
        results = [
            e for e in results
            if query.lower() in (e.get("message", "") + " " +
                                 e.get("service", "")).lower()
        ]
    return {"data": results}


@app.get("/datadog/api/v1/query")
async def dd_metrics_query(
        query: str = Query(""),
        from_ts: str = Query(None, alias="from"),
        to_ts: str = Query(None, alias="to"),
):
    matched = []
    for name, series in DD_METRICS.items():
        if query.lower() in series["metric"].lower():
            matched.append(series)
    if not matched:
        matched = list(DD_METRICS.values())
    return {"series": matched}


# ── Finance Mock ────────────────────────────────────────────────────────


@app.get("/finance/expenses")
async def finance_expenses(status: str = Query(None)):
    results = EXPENSES
    if status:
        results = [e for e in results if e.get("status") == status]
    return {"expenses": results}


@app.get("/finance/expenses/{expense_id}")
async def finance_expense(expense_id: str):
    for exp in EXPENSES:
        if exp.get("expense_id") == expense_id:
            return exp
    return JSONResponse({"error": "Not Found"}, status_code=404)


@app.get("/finance/purchase-orders")
async def finance_purchase_orders(status: str = Query(None)):
    results = PURCHASE_ORDERS
    if status:
        results = [p for p in results if p.get("status") == status]
    return {"purchase_orders": results}


@app.get("/finance/invoices")
async def finance_invoices(status: str = Query(None)):
    results = INVOICES
    if status:
        results = [i for i in results if i.get("status") == status]
    return {"invoices": results}


@app.get("/finance/budgets")
async def finance_budgets():
    return BUDGETS


# ── Customer Support Mock ──────────────────────────────────────────────


@app.get("/customers/accounts")
async def customers_accounts():
    return {"accounts": CUSTOMER_ACCOUNTS}


@app.get("/customers/accounts/{account_id}")
async def customers_account(account_id: str):
    for acct in CUSTOMER_ACCOUNTS:
        if acct.get("account_id") == account_id:
            return acct
    return JSONResponse({"error": "Not Found"}, status_code=404)


@app.get("/customers/escalations")
async def customers_escalations():
    return {"escalations": ESCALATIONS}


@app.get("/customers/escalations/{escalation_id}")
async def customers_escalation(escalation_id: str):
    for esc in ESCALATIONS:
        if esc.get("escalation_id") == escalation_id:
            return esc
    return JSONResponse({"error": "Not Found"}, status_code=404)


# ── Compliance Mock ────────────────────────────────────────────────────


@app.get("/compliance/contracts")
async def compliance_contracts(status: str = Query(None)):
    results = CONTRACTS
    if status:
        results = [c for c in results if c.get("status") == status]
    return {"contracts": results}


@app.get("/compliance/contracts/{contract_id}")
async def compliance_contract(contract_id: str):
    for ctr in CONTRACTS:
        if ctr.get("contract_id") == contract_id:
            return ctr
    return JSONResponse({"error": "Not Found"}, status_code=404)


@app.get("/compliance/audits")
async def compliance_audits():
    return {"audits": AUDITS}


@app.get("/compliance/audits/{audit_id}")
async def compliance_audit(audit_id: str):
    for audit in AUDITS:
        if audit.get("audit_id") == audit_id:
            return audit
    return JSONResponse({"error": "Not Found"}, status_code=404)


@app.get("/compliance/policies")
async def compliance_policies():
    return {"policies": POLICIES}


@app.get("/health")
async def health():
    return {
        "status":
        "ok",
        "services": [
            "slack",
            "github",
            "jira",
            "pagerduty",
            "datadog",
            "finance",
            "customers",
            "compliance",
        ],
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000)
