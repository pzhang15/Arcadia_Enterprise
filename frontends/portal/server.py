import json
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

DISK_ROOT = Path(
    os.environ.get(
        "DISK_ROOT",
        str(
            Path(__file__).resolve().parent.parent.parent / "packages" /
            "eval" / "scenarios" / "northhill_corp" / "fixture" / "disk"),
    ))

app = FastAPI(title="NorthHill Enterprise Portal")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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


# ---------- IT Helpdesk ----------


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


# ---------- HR ----------


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


# ---------- Finance ----------


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


# ---------- Engineering ----------


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


# ---------- Customer Support ----------


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


# ---------- Compliance ----------


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


# ---------- Health ----------


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "disk_root": str(DISK_ROOT),
        "disk_exists": DISK_ROOT.exists()
    }


# ---------- Static files ----------

dist_dir = Path(__file__).parent / "dist"
if dist_dir.exists():
    app.mount("/",
              StaticFiles(directory=str(dist_dir), html=True),
              name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8083)
