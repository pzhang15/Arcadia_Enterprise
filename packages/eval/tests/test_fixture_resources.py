import json
from pathlib import Path

import pytest
from mirage_eval.fixtures import (FakeComplianceResource, FakeCustomersResource,
                                  FakeDatadogResource, FakeFinanceResource,
                                  FakeGDocsResource, FakeGitHubResource,
                                  FakeGSheetsResource, FakePagerDutyResource,
                                  FakePostgresResource, FakeS3Resource,
                                  FakeSlackResource, FakeTicketingResource)

FIXTURE_ROOT = (Path(__file__).resolve().parent.parent / "scenarios" /
                "northhill_corp" / "fixture" / "disk")


@pytest.fixture(scope="module")
def disk_root() -> Path:
    if not FIXTURE_ROOT.exists():
        pytest.skip("northhill_corp fixture not seeded; run "
                    "`uv run mirage-eval seed --scenario northhill_corp`")
    return FIXTURE_ROOT


class TestFakePostgresResource:

    def test_instantiates(self, disk_root: Path):
        r = FakePostgresResource(str(disk_root / "database"))
        assert r is not None

    def test_prompt_contains_table_list(self, disk_root: Path):
        r = FakePostgresResource(str(disk_root / "database"))
        assert "tables" in r.PROMPT

    def test_tables_have_schema_files(self, disk_root: Path):
        tables_dir = disk_root / "database" / "tables"
        assert tables_dir.exists()
        for table_dir in tables_dir.iterdir():
            if not table_dir.is_dir():
                continue
            schema = table_dir / "schema.json"
            assert schema.exists(), f"Missing schema.json for {table_dir.name}"
            data = json.loads(schema.read_text())
            assert "table" in data
            assert "columns" in data
            assert len(data["columns"]) > 0

    def test_tables_have_data_jsonl(self, disk_root: Path):
        tables_dir = disk_root / "database" / "tables"
        for table_dir in tables_dir.iterdir():
            if not table_dir.is_dir():
                continue
            data_file = table_dir / "data.jsonl"
            assert data_file.exists(), f"Missing data.jsonl for {table_dir.name}"
            lines = [
                l for l in data_file.read_text().splitlines() if l.strip()
            ]
            assert len(lines) > 0, f"Empty data.jsonl for {table_dir.name}"
            for line in lines:
                row = json.loads(line)
                assert isinstance(row, dict)

    def test_tables_have_stats(self, disk_root: Path):
        tables_dir = disk_root / "database" / "tables"
        for table_dir in tables_dir.iterdir():
            if not table_dir.is_dir():
                continue
            stats = table_dir / "stats.json"
            assert stats.exists(), f"Missing stats.json for {table_dir.name}"
            data = json.loads(stats.read_text())
            assert data["row_count"] > 0

    def test_expected_tables_exist(self, disk_root: Path):
        tables_dir = disk_root / "database" / "tables"
        expected = {"users", "events", "subscriptions", "invoices"}
        found = {d.name for d in tables_dir.iterdir() if d.is_dir()}
        assert expected <= found, f"Missing tables: {expected - found}"


class TestFakeS3Resource:

    def test_instantiates(self, disk_root: Path):
        r = FakeS3Resource(str(disk_root / "s3"))
        assert r is not None

    def test_prompt_contains_bucket(self, disk_root: Path):
        r = FakeS3Resource(str(disk_root / "s3"))
        assert "northhill-data" in r.PROMPT

    def test_bucket_structure_exists(self, disk_root: Path):
        bucket = disk_root / "s3" / "northhill-data"
        assert bucket.exists()
        expected_dirs = {"logs", "exports", "backups", "artifacts", "reports"}
        found = {d.name for d in bucket.iterdir() if d.is_dir()}
        assert expected_dirs <= found, f"Missing: {expected_dirs - found}"

    def test_logs_contain_entries(self, disk_root: Path):
        logs_dir = disk_root / "s3" / "northhill-data" / "logs"
        assert logs_dir.exists()
        log_files = list(logs_dir.rglob("*.log"))
        assert len(log_files) > 0, "No log files found in S3 logs"
        for log_file in log_files:
            content = log_file.read_text()
            assert len(content.strip()) > 0

    def test_exports_contain_csv(self, disk_root: Path):
        exports_dir = disk_root / "s3" / "northhill-data" / "exports"
        assert exports_dir.exists()
        csv_files = list(exports_dir.rglob("*.csv"))
        assert len(csv_files) > 0, "No CSV exports found"

    def test_deployment_artifacts_exist(self, disk_root: Path):
        artifacts = disk_root / "s3" / "northhill-data" / "artifacts"
        assert artifacts.exists()
        build_logs = list(artifacts.rglob("build.log"))
        assert len(build_logs) > 0, "No deployment build logs found"


class TestFakeFinanceResource:

    def test_instantiates(self, disk_root: Path):
        r = FakeFinanceResource(str(disk_root / "finance"))
        assert r is not None

    def test_expense_structure(self, disk_root: Path):
        expenses = disk_root / "finance" / "expenses"
        assert expenses.exists()
        for status in ("pending", "approved", "rejected"):
            status_dir = expenses / status
            assert status_dir.exists(), f"Missing expenses/{status}"

    def test_expense_json_valid(self, disk_root: Path):
        pending = disk_root / "finance" / "expenses" / "pending"
        files = list(pending.glob("EXP-*.json"))
        assert len(files) > 0, "No pending expenses"
        for f in files:
            data = json.loads(f.read_text())
            assert "expense_id" in data
            assert "amount" in data
            assert "submitter" in data
            assert "status" in data
            assert data["status"] == "pending"

    def test_purchase_orders_structure(self, disk_root: Path):
        po = disk_root / "finance" / "purchase_orders"
        assert po.exists()
        for status in ("open", "approved", "received"):
            status_dir = po / status
            assert status_dir.exists(), f"Missing purchase_orders/{status}"

    def test_invoices_structure(self, disk_root: Path):
        invoices = disk_root / "finance" / "invoices"
        assert invoices.exists()
        for status in ("pending", "paid", "disputed"):
            status_dir = invoices / status
            assert status_dir.exists(), f"Missing invoices/{status}"

    def test_budget_exists(self, disk_root: Path):
        budgets = disk_root / "finance" / "budgets"
        assert budgets.exists()
        budget_files = list(budgets.glob("*.json"))
        assert len(budget_files) > 0, "No budget files"
        data = json.loads(budget_files[0].read_text())
        assert "departments" in data or "total" in data or "quarter" in data


class TestFakeCustomersResource:

    def test_instantiates(self, disk_root: Path):
        r = FakeCustomersResource(str(disk_root / "customers"))
        assert r is not None

    def test_accounts_exist(self, disk_root: Path):
        accounts = disk_root / "customers" / "accounts"
        assert accounts.exists()
        files = list(accounts.glob("ACCT-*.json"))
        assert len(files) >= 3, "Expected at least 3 customer accounts"

    def test_account_schema(self, disk_root: Path):
        accounts = disk_root / "customers" / "accounts"
        for f in accounts.glob("ACCT-*.json"):
            data = json.loads(f.read_text())
            assert "account_id" in data
            assert "company_name" in data
            assert "health_score" in data
            assert isinstance(data["health_score"], (int, float))
            assert 0 <= data["health_score"] <= 100

    def test_escalations_exist(self, disk_root: Path):
        esc = disk_root / "customers" / "escalations"
        assert esc.exists()
        files = list(esc.glob("ESC-*.json"))
        assert len(files) > 0, "No customer escalations found"

    def test_escalation_links_to_account(self, disk_root: Path):
        esc = disk_root / "customers" / "escalations"
        for f in esc.glob("ESC-*.json"):
            data = json.loads(f.read_text())
            assert "account_id" in data
            assert data["account_id"].startswith("ACCT-")


class TestFakeComplianceResource:

    def test_instantiates(self, disk_root: Path):
        r = FakeComplianceResource(str(disk_root / "compliance"))
        assert r is not None

    def test_contracts_structure(self, disk_root: Path):
        contracts = disk_root / "compliance" / "contracts"
        assert contracts.exists()
        for status in ("active", "in_review"):
            status_dir = contracts / status
            assert status_dir.exists(), f"Missing contracts/{status}"

    def test_contract_schema(self, disk_root: Path):
        contracts = disk_root / "compliance" / "contracts"
        all_contracts = list(contracts.rglob("CTR-*.json"))
        assert len(all_contracts) >= 3
        for f in all_contracts:
            data = json.loads(f.read_text())
            assert "contract_id" in data
            assert "counterparty" in data
            assert "status" in data

    def test_audits_exist(self, disk_root: Path):
        audits = disk_root / "compliance" / "audits"
        assert audits.exists()
        files = list(audits.glob("AUDIT-*.json"))
        assert len(files) > 0
        for f in files:
            data = json.loads(f.read_text())
            assert "audit_id" in data
            assert "framework" in data
            assert "checklist" in data
            assert len(data["checklist"]) > 0

    def test_policies_exist(self, disk_root: Path):
        policies = disk_root / "compliance" / "policies"
        assert policies.exists()
        files = list(policies.glob("POL-*.json"))
        assert len(files) > 0
        for f in files:
            data = json.loads(f.read_text())
            assert "policy_id" in data
            assert "title" in data


class TestFakeSlackResource:

    def test_instantiates(self, disk_root: Path):
        r = FakeSlackResource(str(disk_root / "slack"))
        assert r is not None

    def test_channels_exist(self, disk_root: Path):
        channels = disk_root / "slack" / "channels"
        assert channels.exists()
        channel_dirs = [d for d in channels.iterdir() if d.is_dir()]
        assert len(channel_dirs) >= 5, (
            f"Expected at least 5 channels, found {len(channel_dirs)}")

    def test_chat_files_are_jsonl(self, disk_root: Path):
        channels = disk_root / "slack" / "channels"
        chat_files = list(channels.rglob("chat.jsonl"))
        assert len(chat_files) > 0
        for f in chat_files[:3]:
            for line in f.read_text().splitlines():
                if line.strip():
                    msg = json.loads(line)
                    assert "user" in msg or "author" in msg or "sender" in msg


class TestFakeGitHubResource:

    def test_instantiates(self, disk_root: Path):
        r = FakeGitHubResource(str(disk_root / "github"))
        assert r is not None

    def test_deployments_exist(self, disk_root: Path):
        github = disk_root / "github"
        deployments = list(github.rglob("deployments"))
        assert len(deployments) > 0
        deploy_files = list(github.rglob("deployments/*.json"))
        assert len(deploy_files) > 0

    def test_commits_exist(self, disk_root: Path):
        github = disk_root / "github"
        commit_files = list(github.rglob("commits/*.json"))
        assert len(commit_files) > 0
        for f in commit_files:
            data = json.loads(f.read_text())
            assert "sha" in data or "commit" in data or "message" in data


class TestFakePagerDutyResource:

    def test_instantiates(self, disk_root: Path):
        r = FakePagerDutyResource(str(disk_root / "pagerduty"))
        assert r is not None

    def test_incidents_exist(self, disk_root: Path):
        pd = disk_root / "pagerduty" / "incidents"
        assert pd.exists()
        incident_files = list(pd.rglob("INC-*.json"))
        assert len(incident_files) > 0

    def test_services_exist(self, disk_root: Path):
        services = disk_root / "pagerduty" / "services"
        assert services.exists()
        svc_files = list(services.glob("*.json"))
        assert len(svc_files) > 0


class TestFakeDatadogResource:

    def test_instantiates(self, disk_root: Path):
        r = FakeDatadogResource(str(disk_root / "datadog"))
        assert r is not None

    def test_logs_exist(self, disk_root: Path):
        logs = disk_root / "datadog" / "logs"
        assert logs.exists()
        log_files = list(logs.rglob("*.jsonl"))
        assert len(log_files) > 0

    def test_metrics_exist(self, disk_root: Path):
        metrics = disk_root / "datadog" / "metrics"
        assert metrics.exists()
        metric_files = list(metrics.rglob("*.json"))
        assert len(metric_files) > 0
