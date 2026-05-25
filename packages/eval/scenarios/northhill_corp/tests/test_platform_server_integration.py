import json
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from scenarios.northhill_corp import seed

_REPO_ROOT = Path(__file__).resolve()
while _REPO_ROOT != _REPO_ROOT.parent:
    if (_REPO_ROOT / "pyproject.toml").exists() and (
            _REPO_ROOT / "frontends").exists():
        break
    _REPO_ROOT = _REPO_ROOT.parent

_SERVER_DIR = _REPO_ROOT / "frontends" / "platform"
if str(_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(_SERVER_DIR))


@pytest.fixture
def _seeded_disk(tmp_path):
    seed.main(str(tmp_path), clean=True)
    return tmp_path


@pytest.fixture
def _app(_seeded_disk):
    import importlib

    import server as _server_mod

    importlib.reload(_server_mod)
    _server_mod.DISK_ROOT = _seeded_disk
    _server_mod.OPENAI_API_KEY = ""
    _server_mod._sessions.clear()
    _server_mod._event_buffer.clear()
    return _server_mod.app


@pytest.fixture
async def client(_app):
    transport = ASGITransport(app=_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health_reports_disk_exists(self, client):
        resp = await client.get("/api/health")
        data = resp.json()
        assert data["disk_exists"] is True

    @pytest.mark.asyncio
    async def test_health_reports_disk_subdirs(self, client):
        resp = await client.get("/api/health")
        data = resp.json()
        expected = {
            "compliance", "customers", "datadog", "finance", "gdocs",
            "github", "pagerduty", "sheets", "slack", "tickets"
        }
        assert expected.issubset(set(data["disk_subdirs"]))

    @pytest.mark.asyncio
    async def test_health_reports_mirage_available(self, client):
        resp = await client.get("/api/health")
        data = resp.json()
        assert data["has_mirage"] is True

    @pytest.mark.asyncio
    async def test_health_reports_eval_package(self, client):
        resp = await client.get("/api/health")
        data = resp.json()
        assert data["has_eval_package"] is True


class TestSessionWorkspace:
    @pytest.mark.asyncio
    async def test_create_session_has_workspace(self, client):
        resp = await client.post("/api/sessions",
                                 json={"services": ["it", "finance"]})
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_workspace"] is True
        assert data["id"]
        assert data["services"] == ["it", "finance"]

    @pytest.mark.asyncio
    async def test_create_session_empty_services(self, client):
        resp = await client.post("/api/sessions", json={"services": []})
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_workspace"] is True

    @pytest.mark.asyncio
    async def test_session_listed_after_creation(self, client):
        await client.post("/api/sessions",
                          json={"services": ["it"]})
        resp = await client.get("/api/sessions")
        assert resp.status_code == 200
        sessions = resp.json()
        assert len(sessions) >= 1

    @pytest.mark.asyncio
    async def test_session_status_returns_ready(self, client):
        create_resp = await client.post("/api/sessions",
                                        json={"services": ["it"]})
        sid = create_resp.json()["id"]
        resp = await client.get(f"/api/sessions/{sid}/status")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"


class TestAgentConsoleWithWorkspace:
    @pytest.mark.asyncio
    async def test_message_without_api_key_gives_clear_error(self, client):
        create_resp = await client.post(
            "/api/sessions", json={"services": ["it"]})
        sid = create_resp.json()["id"]
        resp = await client.post(f"/api/sessions/{sid}/message",
                                 json={"message": "List open IT tickets"})
        assert resp.status_code == 200
        data = resp.json()
        assert "OPENAI_API_KEY" in data["reply"]
        assert "Portal" in data["reply"]

    @pytest.mark.asyncio
    async def test_message_with_api_key_calls_openai(self, client, _app):
        import server as _server_mod

        _server_mod.OPENAI_API_KEY = "test-key-fake"
        create_resp = await client.post(
            "/api/sessions", json={"services": ["it"]})
        sid = create_resp.json()["id"]

        mock_resp = AsyncMock()
        mock_resp.choices = [
            type("Choice", (), {
                "message": type("Msg", (), {"content": "Here are the tickets."})()
            })()
        ]
        mock_create = AsyncMock(return_value=mock_resp)

        with patch.object(_server_mod, "_get_openai_client") as mock_client:
            mock_client.return_value.chat.completions.create = mock_create
            resp = await client.post(
                f"/api/sessions/{sid}/message",
                json={"message": "List open IT tickets"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["reply"] == "Here are the tickets."
        assert data["status"] == "ready"

    @pytest.mark.asyncio
    async def test_exec_command_uses_workspace(self, client, _app):
        """When the LLM returns EXEC: commands, the workspace executes them."""
        import server as _server_mod

        _server_mod.OPENAI_API_KEY = "test-key-fake"
        create_resp = await client.post(
            "/api/sessions", json={"services": ["it"]})
        sid = create_resp.json()["id"]

        call_count = 0

        async def mock_create(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                content = (
                    "Let me check the tickets.\n"
                    "EXEC: ls /tickets/queues/it-helpdesk/open/")
            else:
                content = "I found the open IT tickets in the workspace."
            resp = AsyncMock()
            resp.choices = [
                type("Choice", (), {
                    "message": type("Msg", (), {"content": content})()
                })()
            ]
            return resp

        with patch.object(_server_mod, "_get_openai_client") as mock_client:
            mock_client.return_value.chat.completions.create = AsyncMock(
                side_effect=mock_create)
            resp = await client.post(
                f"/api/sessions/{sid}/message",
                json={"message": "Check IT tickets"})

        assert resp.status_code == 200
        data = resp.json()
        assert "found" in data["reply"].lower() or "tickets" in data["reply"].lower()
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_session_not_found(self, client):
        resp = await client.post(
            "/api/sessions/nonexistent/message",
            json={"message": "hello"})
        assert resp.status_code == 404


class TestPortalEndpoints:
    @pytest.mark.asyncio
    async def test_tickets_it_helpdesk(self, client):
        resp = await client.get("/api/tickets/it-helpdesk")
        assert resp.status_code == 200
        tickets = resp.json()
        assert len(tickets) >= 3
        for t in tickets:
            assert "ticket_id" in t

    @pytest.mark.asyncio
    async def test_tickets_customer_support(self, client):
        resp = await client.get("/api/tickets/customer-support")
        assert resp.status_code == 200
        tickets = resp.json()
        assert len(tickets) >= 1

    @pytest.mark.asyncio
    async def test_expenses(self, client):
        resp = await client.get("/api/finance/expenses")
        assert resp.status_code == 200
        expenses = resp.json()
        assert len(expenses) >= 3
        for e in expenses:
            assert "expense_id" in e

    @pytest.mark.asyncio
    async def test_purchase_orders(self, client):
        resp = await client.get("/api/finance/purchase-orders")
        assert resp.status_code == 200
        pos = resp.json()
        assert len(pos) >= 2

    @pytest.mark.asyncio
    async def test_invoices(self, client):
        resp = await client.get("/api/finance/invoices")
        assert resp.status_code == 200
        invoices = resp.json()
        assert len(invoices) >= 2

    @pytest.mark.asyncio
    async def test_budgets(self, client):
        resp = await client.get("/api/finance/budgets")
        assert resp.status_code == 200
        data = resp.json()
        assert "departments" in data
        assert len(data["departments"]) >= 1

    @pytest.mark.asyncio
    async def test_incidents(self, client):
        resp = await client.get("/api/engineering/incidents")
        assert resp.status_code == 200
        incidents = resp.json()
        assert len(incidents) >= 1
        for inc in incidents:
            assert "id" in inc
            assert "status" in inc

    @pytest.mark.asyncio
    async def test_deployments(self, client):
        resp = await client.get("/api/engineering/deployments")
        assert resp.status_code == 200
        deploys = resp.json()
        assert len(deploys) >= 1

    @pytest.mark.asyncio
    async def test_metrics(self, client):
        resp = await client.get("/api/engineering/metrics")
        assert resp.status_code == 200
        metrics = resp.json()
        assert len(metrics) >= 1

    @pytest.mark.asyncio
    async def test_customer_accounts(self, client):
        resp = await client.get("/api/customers/accounts")
        assert resp.status_code == 200
        accounts = resp.json()
        assert len(accounts) >= 3
        for acct in accounts:
            assert "account_id" in acct or "id" in acct

    @pytest.mark.asyncio
    async def test_customer_escalations(self, client):
        resp = await client.get("/api/customers/escalations")
        assert resp.status_code == 200
        escalations = resp.json()
        assert len(escalations) >= 2

    @pytest.mark.asyncio
    async def test_compliance_contracts(self, client):
        resp = await client.get("/api/compliance/contracts")
        assert resp.status_code == 200
        contracts = resp.json()
        assert len(contracts) >= 3

    @pytest.mark.asyncio
    async def test_compliance_audits(self, client):
        resp = await client.get("/api/compliance/audits")
        assert resp.status_code == 200
        audits = resp.json()
        assert len(audits) >= 1

    @pytest.mark.asyncio
    async def test_compliance_policies(self, client):
        resp = await client.get("/api/compliance/policies")
        assert resp.status_code == 200
        policies = resp.json()
        assert len(policies) >= 1


class TestDiskWorkspaceFallback:
    @pytest.mark.asyncio
    async def test_disk_workspace_has_writable_root(self, _seeded_disk):
        import server as _server_mod

        _server_mod.DISK_ROOT = _seeded_disk
        ws = _server_mod._build_disk_workspace()
        assert ws is not None
        result = await ws.execute("echo hello > /test_write.txt")
        assert result.exit_code == 0
        result2 = await ws.execute("cat /test_write.txt")
        assert "hello" in result2.stdout.decode()

    @pytest.mark.asyncio
    async def test_disk_workspace_mounts_all_services(self, _seeded_disk):
        import server as _server_mod

        _server_mod.DISK_ROOT = _seeded_disk
        ws = _server_mod._build_disk_workspace()
        assert ws is not None
        result = await ws.execute("ls /")
        stdout = result.stdout.decode()
        for expected in ("tickets", "finance", "compliance", "customers",
                         "pagerduty", "datadog", "slack", "sheets"):
            assert expected in stdout, f"Missing mount: {expected}"

    @pytest.mark.asyncio
    async def test_disk_workspace_returns_none_when_no_disk(self):
        import server as _server_mod

        original = _server_mod.DISK_ROOT
        _server_mod.DISK_ROOT = Path("/nonexistent/path")
        try:
            ws = _server_mod._build_disk_workspace()
            assert ws is None
        finally:
            _server_mod.DISK_ROOT = original


class TestQuickActions:
    @pytest.mark.asyncio
    async def test_quick_actions_list(self, client):
        resp = await client.get("/api/quick-actions")
        assert resp.status_code == 200
        actions = resp.json()
        assert len(actions) >= 5
        ids = {a["id"] for a in actions}
        assert "triage" in ids
        assert "expenses" in ids
        assert "incident" in ids


class TestConfig:
    @pytest.mark.asyncio
    async def test_config_without_api_key(self, client):
        resp = await client.get("/api/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_api_key"] is False
        assert "model" in data
