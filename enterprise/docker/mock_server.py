import json
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scenarios.meridian_labs.seed import (
    CHANNEL_MESSAGES,
    CHANNELS,
    USERS,
    _slack_msg,
    _slugify,
    _user_obj,
)

app = FastAPI(title="Mirage Mock Services")

_posted_messages: list[dict] = []
_ticket_comments: dict[str, list[dict]] = {}


def _seed_tickets():
    from scenarios.meridian_labs.seed import main as seed_main
    import tempfile
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
    from scenarios.meridian_labs.seed import main as seed_main
    import tempfile
    td = Path(tempfile.mkdtemp(prefix="mock-seed-"))
    seed_main(td, clean=True)
    gh = td / "github" / "repos" / "meridian-labs" / "payments-api"
    deployments = [json.loads(f.read_text())
                   for f in sorted((gh / "deployments").glob("*.json"))]
    commits = {f.stem: json.loads(f.read_text())
               for f in (gh / "commits").glob("*.json")}
    pulls = [json.loads(f.read_text())
             for f in sorted((gh / "pulls").glob("*.json"))]
    return deployments, commits, pulls


def _seed_pagerduty():
    from scenarios.meridian_labs.seed import main as seed_main
    import tempfile
    td = Path(tempfile.mkdtemp(prefix="mock-seed-"))
    seed_main(td, clean=True)
    pd = td / "pagerduty"
    services = [json.loads(f.read_text())
                for f in sorted((pd / "services").glob("*.json"))]
    incidents = []
    for status in ("triggered", "acknowledged", "resolved"):
        d = pd / "incidents" / status
        if d.exists():
            for f in sorted(d.glob("*.json")):
                incidents.append(json.loads(f.read_text()))
    return services, incidents


def _seed_datadog():
    from scenarios.meridian_labs.seed import main as seed_main
    import tempfile
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


TICKETS = _seed_tickets()
GH_DEPLOYMENTS, GH_COMMITS, GH_PULLS = _seed_github()
PD_SERVICES, PD_INCIDENTS = _seed_pagerduty()
DD_LOGS, DD_METRICS = _seed_datadog()


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
        "message": {"text": body.get("text", "")},
    }


@app.get("/slack/api/users.list")
async def slack_users_list():
    members = [{"id": u["id"], "name": u["handle"],
                "real_name": u["name"],
                "profile": {"title": u["title"], "email": u["email"]}}
               for u in USERS]
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
            results = [t for t in results
                       if t.get("project", "").upper() == project]
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
    comment = {"author": body.get("author", "agent"),
               "body": body.get("body", ""),
               "created": "2026-05-15T15:00:00Z"}
    _ticket_comments.setdefault(key, []).append(comment)
    return comment


@app.get("/jira/rest/api/2/project")
async def jira_projects():
    return [{"key": "OPS", "name": "Operations"},
            {"key": "PAY", "name": "Payments"}]


# ── PagerDuty Mock ──────────────────────────────────────────────────────

@app.get("/pagerduty/incidents")
async def pd_incidents(
    statuses: list[str] = Query(None, alias="statuses[]"),
):
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
        results = [e for e in results if query.lower() in
                   (e.get("message", "") + " " +
                    e.get("service", "")).lower()]
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


@app.get("/health")
async def health():
    return {"status": "ok", "services": [
        "slack", "github", "jira", "pagerduty", "datadog"]}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000)
