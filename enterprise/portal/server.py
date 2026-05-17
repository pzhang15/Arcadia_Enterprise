import json
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

DISK_ROOT = Path(os.environ.get(
    "DISK_ROOT",
    str(Path(__file__).resolve().parent.parent / "scenarios" / "acme_corp" /
        "fixture" / "disk"),
))

app = FastAPI(title="ACME Enterprise Portal")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_cache: dict[str, object] = {}


def _load_json(rel: str) -> object:
    if rel in _cache:
        return _cache[rel]
    path = DISK_ROOT / rel
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    _cache[rel] = data
    return data


def _load_dir_jsons(rel: str) -> list[dict]:
    d = DISK_ROOT / rel
    if not d.exists() or not d.is_dir():
        return []
    results = []
    for f in sorted(d.iterdir()):
        if f.suffix == ".json":
            results.append(json.loads(f.read_text()))
    return results


def _load_users() -> list[dict]:
    data = _load_json("slack/users.json")
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "members" in data:
        return data["members"]
    return []


# ---------- IT Helpdesk ----------

@app.get("/api/tickets/{queue}")
async def list_tickets(queue: str) -> list[dict]:
    return _load_dir_jsons(f"tickets/{queue}")


@app.get("/api/tickets/{queue}/{ticket_id}")
async def get_ticket(queue: str, ticket_id: str) -> dict:
    data = _load_json(f"tickets/{queue}/{ticket_id}.json")
    if data is None:
        return {"error": "not found"}
    return data


# ---------- HR ----------

@app.get("/api/employees")
async def list_employees() -> list[dict]:
    return _load_users()


@app.get("/api/sheets/{sheet_id}")
async def get_sheet(sheet_id: str) -> dict:
    data = _load_json(f"sheets/{sheet_id}.json")
    if data is None:
        return {"error": "not found"}
    return data


# ---------- Finance ----------

@app.get("/api/finance/expenses")
async def list_expenses() -> list[dict]:
    return _load_dir_jsons("finance/expenses")


@app.get("/api/finance/purchase-orders")
async def list_purchase_orders() -> list[dict]:
    return _load_dir_jsons("finance/purchase_orders")


@app.get("/api/finance/invoices")
async def list_invoices() -> list[dict]:
    return _load_dir_jsons("finance/invoices")


@app.get("/api/finance/budgets")
async def get_budgets() -> dict:
    data = _load_json("finance/budgets.json")
    if data is None:
        return {"departments": []}
    return data


# ---------- Engineering ----------

@app.get("/api/engineering/incidents")
async def list_incidents() -> list[dict]:
    return _load_dir_jsons("pagerduty/incidents")


@app.get("/api/engineering/deployments")
async def list_deployments() -> list[dict]:
    return _load_dir_jsons("github/deployments")


@app.get("/api/engineering/metrics")
async def get_metrics() -> dict:
    data = _load_json("datadog/metrics.json")
    if data is None:
        return {"series": []}
    return data


# ---------- Customer Support ----------

@app.get("/api/customers/accounts")
async def list_accounts() -> list[dict]:
    return _load_dir_jsons("customers/accounts")


@app.get("/api/customers/escalations")
async def list_escalations() -> list[dict]:
    return _load_dir_jsons("customers/escalations")


# ---------- Compliance ----------

@app.get("/api/compliance/contracts")
async def list_contracts() -> list[dict]:
    return _load_dir_jsons("compliance/contracts")


@app.get("/api/compliance/audits")
async def list_audits() -> list[dict]:
    return _load_dir_jsons("compliance/audits")


@app.get("/api/compliance/policies")
async def list_policies() -> list[dict]:
    return _load_dir_jsons("compliance/policies")


# ---------- Health ----------

@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "disk_root": str(DISK_ROOT),
            "disk_exists": DISK_ROOT.exists()}


# ---------- Static files ----------

dist_dir = Path(__file__).parent / "dist"
if dist_dir.exists():
    app.mount("/", StaticFiles(directory=str(dist_dir), html=True),
              name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8083)
