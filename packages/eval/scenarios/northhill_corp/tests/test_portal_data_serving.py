import json
from pathlib import Path

import pytest


def _load_dir_jsons(d: Path) -> list[dict]:
    if not d.exists() or not d.is_dir():
        return []
    results = []
    for f in sorted(d.iterdir()):
        if f.suffix == ".json":
            results.append(json.loads(f.read_text()))
    return results


def _load_dir_jsons_recursive(d: Path) -> list[dict]:
    if not d.exists() or not d.is_dir():
        return []
    results = []
    for f in sorted(d.rglob("*.json")):
        results.append(json.loads(f.read_text()))
    return results


class TestPortalTickets:
    def test_it_helpdesk_tickets_loadable(self, disk_root):
        tickets = _load_dir_jsons_recursive(
            disk_root / "tickets" / "queues" / "it-helpdesk"
        )
        assert len(tickets) >= 3
        for t in tickets:
            assert "ticket_id" in t or "id" in t

    def test_customer_support_tickets_loadable(self, disk_root):
        tickets = _load_dir_jsons_recursive(
            disk_root / "tickets" / "queues" / "customer-support"
        )
        assert len(tickets) >= 3

    def test_legal_tickets_loadable(self, disk_root):
        tickets = _load_dir_jsons_recursive(
            disk_root / "tickets" / "queues" / "legal"
        )
        assert len(tickets) >= 1


class TestPortalEmployees:
    def test_employees_from_slack_users(self, disk_root):
        users = _load_dir_jsons(disk_root / "slack" / "users")
        assert len(users) >= 10
        for u in users:
            assert "id" in u
            assert "name" in u or "real_name" in u


class TestPortalSheets:
    def test_sheets_list(self, disk_root):
        sheets = _load_dir_jsons(disk_root / "sheets" / "owned")
        assert len(sheets) >= 3

    def test_sheet_lookup_by_id(self, disk_root):
        owned = disk_root / "sheets" / "owned"
        assert owned.exists()
        found = False
        for f in owned.iterdir():
            if "SH101" in f.name and f.suffix == ".json":
                data = json.loads(f.read_text())
                assert data is not None
                found = True
                break
        assert found, "New Hire Tracker sheet (SH101) not found"


class TestPortalFinance:
    def test_expenses_all_statuses(self, disk_root):
        expenses = _load_dir_jsons_recursive(disk_root / "finance" / "expenses")
        assert len(expenses) >= 3
        statuses = {e.get("status") for e in expenses}
        assert "pending" in statuses, "No pending expenses"
        assert "approved" in statuses, "No approved expenses"

    def test_purchase_orders(self, disk_root):
        pos = _load_dir_jsons_recursive(disk_root / "finance" / "purchase_orders")
        assert len(pos) >= 2

    def test_invoices(self, disk_root):
        invoices = _load_dir_jsons_recursive(disk_root / "finance" / "invoices")
        assert len(invoices) >= 2

    def test_budgets(self, disk_root):
        budget_file = disk_root / "finance" / "budgets" / "Q2_2026.json"
        assert budget_file.exists()
        data = json.loads(budget_file.read_text())
        assert "departments" in data
        assert len(data["departments"]) >= 1


class TestPortalEngineering:
    def test_incidents(self, disk_root):
        incidents = _load_dir_jsons_recursive(disk_root / "pagerduty" / "incidents")
        assert len(incidents) >= 1

    def test_deployments(self, disk_root):
        gh = disk_root / "github"
        assert gh.exists()
        results = []
        for f in sorted(gh.rglob("deployments/*.json")):
            results.append(json.loads(f.read_text()))
        assert len(results) >= 1

    def test_metrics(self, disk_root):
        metrics = _load_dir_jsons_recursive(
            disk_root / "datadog" / "metrics"
        )
        assert len(metrics) >= 1


class TestPortalCustomers:
    def test_accounts(self, disk_root):
        accounts = _load_dir_jsons(disk_root / "customers" / "accounts")
        assert len(accounts) >= 3
        for acct in accounts:
            assert "account_id" in acct
            assert "health_score" in acct

    def test_escalations(self, disk_root):
        escalations = _load_dir_jsons(disk_root / "customers" / "escalations")
        assert len(escalations) >= 2


class TestPortalCompliance:
    def test_contracts(self, disk_root):
        contracts = _load_dir_jsons_recursive(
            disk_root / "compliance" / "contracts"
        )
        assert len(contracts) >= 3

    def test_audits(self, disk_root):
        audits = _load_dir_jsons(disk_root / "compliance" / "audits")
        assert len(audits) >= 1

    def test_policies(self, disk_root):
        policies = _load_dir_jsons(disk_root / "compliance" / "policies")
        assert len(policies) >= 1


class TestPortalEnvVarConfig:
    @staticmethod
    def _repo_root() -> Path:
        p = Path(__file__).resolve()
        while p != p.parent:
            if (p / "pyproject.toml").exists() and (p / "frontends").exists():
                return p
            p = p.parent
        raise FileNotFoundError("repo root not found")

    def test_disk_root_env_var_name(self):
        """The platform server reads DISK_ROOT."""
        server_path = self._repo_root() / "frontends" / "platform" / "server.py"
        content = server_path.read_text()
        assert "DISK_ROOT" in content, \
            "Platform server should read DISK_ROOT env var"

    def test_docker_compose_sets_disk_root(self):
        """docker-compose should set DISK_ROOT for the platform."""
        compose_path = self._repo_root() / "docker" / "docker-compose.yml"
        content = compose_path.read_text()
        assert "DISK_ROOT=/app/fixture" in content, \
            "docker-compose should set DISK_ROOT=/app/fixture for arcadia-platform"
