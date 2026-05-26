import json
import tempfile
from pathlib import Path

import pytest
from scenarios.northhill_corp.seed import main as seed_main


@pytest.fixture(scope="module")
def seeded_root() -> Path:
    tmp = tempfile.mkdtemp(prefix="northhill_seed_test_")
    root = Path(tmp)
    seed_main(str(root), clean=True)
    return root


class TestSeedCompleteness:

    def test_all_mount_dirs_created(self, seeded_root: Path):
        expected = {
            "slack", "sheets", "gdocs", "tickets", "github", "pagerduty",
            "datadog", "finance", "customers", "compliance", "database", "s3"
        }
        found = {d.name for d in seeded_root.iterdir() if d.is_dir()}
        assert expected <= found, f"Missing: {expected - found}"

    def test_slack_has_multiple_channels(self, seeded_root: Path):
        channels = seeded_root / "slack" / "channels"
        assert channels.exists()
        dirs = [d for d in channels.iterdir() if d.is_dir()]
        assert len(dirs) >= 5

    def test_slack_channels_have_chat_data(self, seeded_root: Path):
        channels = seeded_root / "slack" / "channels"
        for ch_dir in channels.iterdir():
            if not ch_dir.is_dir():
                continue
            chat_files = list(ch_dir.rglob("chat.jsonl"))
            assert len(chat_files) > 0, (
                f"Channel {ch_dir.name} has no chat data")

    def test_tickets_has_multiple_queues(self, seeded_root: Path):
        queues = seeded_root / "tickets" / "queues"
        assert queues.exists()
        queue_dirs = [d for d in queues.iterdir() if d.is_dir()]
        assert len(queue_dirs) >= 2

    def test_tickets_have_statuses(self, seeded_root: Path):
        queues = seeded_root / "tickets" / "queues"
        for queue_dir in queues.iterdir():
            if not queue_dir.is_dir():
                continue
            statuses = {
                d.name
                for d in queue_dir.iterdir() if d.is_dir()
            }
            assert "open" in statuses or "in_progress" in statuses or \
                "resolved" in statuses, (
                    f"Queue {queue_dir.name} has no status dirs")

    def test_database_four_tables(self, seeded_root: Path):
        tables = seeded_root / "database" / "tables"
        assert tables.exists()
        table_dirs = {d.name for d in tables.iterdir() if d.is_dir()}
        expected = {"users", "events", "subscriptions", "invoices"}
        assert expected <= table_dirs

    def test_database_table_schemas_valid(self, seeded_root: Path):
        tables = seeded_root / "database" / "tables"
        for table_dir in tables.iterdir():
            if not table_dir.is_dir():
                continue
            schema = json.loads((table_dir / "schema.json").read_text())
            assert schema["table"] == table_dir.name
            assert len(schema["columns"]) > 0
            for col in schema["columns"]:
                assert "name" in col
                assert "type" in col

    def test_database_data_row_count_matches_stats(self, seeded_root: Path):
        tables = seeded_root / "database" / "tables"
        for table_dir in tables.iterdir():
            if not table_dir.is_dir():
                continue
            stats = json.loads((table_dir / "stats.json").read_text())
            data_lines = [
                l for l in (table_dir / "data.jsonl").read_text().splitlines()
                if l.strip()
            ]
            assert stats["row_count"] == len(data_lines), (
                f"Table {table_dir.name}: stats says {stats['row_count']} "
                f"rows but data.jsonl has {len(data_lines)}")

    def test_s3_bucket_structure(self, seeded_root: Path):
        bucket = seeded_root / "s3" / "northhill-data"
        assert bucket.exists()
        expected = {"logs", "exports", "backups", "artifacts", "reports"}
        found = {d.name for d in bucket.iterdir() if d.is_dir()}
        assert expected <= found

    def test_s3_logs_have_daily_files(self, seeded_root: Path):
        logs = seeded_root / "s3" / "northhill-data" / "logs"
        log_files = list(logs.rglob("app.log"))
        assert len(log_files) >= 3, "Expected at least 3 daily log files"

    def test_s3_exports_have_csv(self, seeded_root: Path):
        exports = seeded_root / "s3" / "northhill-data" / "exports"
        csv_files = list(exports.rglob("*.csv"))
        assert len(csv_files) >= 2, "Expected at least 2 CSV exports"

    def test_finance_expenses_volume(self, seeded_root: Path):
        expenses = seeded_root / "finance" / "expenses"
        all_expenses = list(expenses.rglob("EXP-*.json"))
        assert len(all_expenses) >= 6, (
            f"Expected at least 6 expenses, found {len(all_expenses)}")

    def test_finance_purchase_orders_volume(self, seeded_root: Path):
        po = seeded_root / "finance" / "purchase_orders"
        all_po = list(po.rglob("PO-*.json"))
        assert len(all_po) >= 4

    def test_finance_invoices_volume(self, seeded_root: Path):
        invoices = seeded_root / "finance" / "invoices"
        all_inv = list(invoices.rglob("INV-*.json"))
        assert len(all_inv) >= 4

    def test_customers_accounts_volume(self, seeded_root: Path):
        accounts = seeded_root / "customers" / "accounts"
        all_acct = list(accounts.glob("ACCT-*.json"))
        assert len(all_acct) >= 4

    def test_customers_escalations_reference_accounts(self, seeded_root: Path):
        accounts = seeded_root / "customers" / "accounts"
        acct_ids = set()
        for f in accounts.glob("ACCT-*.json"):
            data = json.loads(f.read_text())
            acct_ids.add(data["account_id"])

        escalations = seeded_root / "customers" / "escalations"
        for f in escalations.glob("ESC-*.json"):
            data = json.loads(f.read_text())
            assert data["account_id"] in acct_ids, (
                f"Escalation {data['escalation_id']} references unknown "
                f"account {data['account_id']}")

    def test_compliance_contracts_have_valid_types(self, seeded_root: Path):
        contracts = seeded_root / "compliance" / "contracts"
        valid_types = {"NDA", "MSA", "SOW", "DPA"}
        for f in contracts.rglob("CTR-*.json"):
            data = json.loads(f.read_text())
            assert data["type"] in valid_types, (
                f"Contract {data['contract_id']} has invalid type {data['type']}")

    def test_compliance_audits_have_checklists(self, seeded_root: Path):
        audits = seeded_root / "compliance" / "audits"
        for f in audits.glob("AUDIT-*.json"):
            data = json.loads(f.read_text())
            assert "checklist" in data
            assert len(data["checklist"]) >= 3

    def test_compliance_policies_have_acknowledgments(self, seeded_root: Path):
        policies = seeded_root / "compliance" / "policies"
        for f in policies.glob("POL-*.json"):
            data = json.loads(f.read_text())
            assert "acknowledgments" in data

    def test_pagerduty_has_triggered_incident(self, seeded_root: Path):
        triggered = seeded_root / "pagerduty" / "incidents" / "triggered"
        if triggered.exists():
            files = list(triggered.glob("*.json"))
            assert len(files) > 0
            for f in files:
                data = json.loads(f.read_text())
                assert "incident_id" in data or "id" in data

    def test_github_has_deployments(self, seeded_root: Path):
        github = seeded_root / "github"
        deploy_files = list(github.rglob("deployments/*.json"))
        assert len(deploy_files) >= 2

    def test_github_has_commits(self, seeded_root: Path):
        github = seeded_root / "github"
        commit_files = list(github.rglob("commits/*.json"))
        assert len(commit_files) >= 2

    def test_datadog_logs_contain_entries(self, seeded_root: Path):
        logs = seeded_root / "datadog" / "logs"
        jsonl_files = list(logs.rglob("*.jsonl"))
        assert len(jsonl_files) > 0
        for f in jsonl_files:
            lines = [l for l in f.read_text().splitlines() if l.strip()]
            assert len(lines) > 0

    def test_datadog_metrics_exist(self, seeded_root: Path):
        metrics = seeded_root / "datadog" / "metrics"
        metric_files = list(metrics.rglob("*.json"))
        assert len(metric_files) > 0


class TestSeedCrossReferences:

    def test_incident_references_deployment(self, seeded_root: Path):
        """INC-5521 should reference a deployment or commit."""
        triggered = seeded_root / "pagerduty" / "incidents" / "triggered"
        if not triggered.exists():
            pytest.skip("No triggered incidents")
        for f in triggered.glob("*.json"):
            data = json.loads(f.read_text())
            incident_id = data.get("incident_id") or data.get("id", "")
            if "5521" in str(incident_id):
                assert ("deployment" in json.dumps(data).lower()
                        or "commit" in json.dumps(data).lower()
                        or "description" in data)
                return
        pytest.skip("INC-5521 not in triggered incidents")

    def test_customer_ticket_links_to_account(self, seeded_root: Path):
        """Support tickets should link to customer accounts."""
        cs_queue = (seeded_root / "tickets" / "queues" / "customer-support")
        if not cs_queue.exists():
            pytest.skip("No customer-support queue")
        all_tickets = list(cs_queue.rglob("*.json"))
        assert len(all_tickets) > 0
        linked_count = 0
        for f in all_tickets:
            data = json.loads(f.read_text())
            content = json.dumps(data).lower()
            if "acct-" in content or "account" in content:
                linked_count += 1
        assert linked_count > 0, (
            "No customer support tickets reference an account")

    def test_seed_is_deterministic(self):
        """Running seed twice produces identical output."""
        import tempfile
        tmp1 = Path(tempfile.mkdtemp(prefix="seed_det_1_"))
        tmp2 = Path(tempfile.mkdtemp(prefix="seed_det_2_"))
        seed_main(str(tmp1), clean=True)
        seed_main(str(tmp2), clean=True)

        files1 = sorted(
            str(p.relative_to(tmp1)) for p in tmp1.rglob("*") if p.is_file())
        files2 = sorted(
            str(p.relative_to(tmp2)) for p in tmp2.rglob("*") if p.is_file())
        assert files1 == files2, "Seed produced different file sets"

        for rel in files1[:20]:
            content1 = (tmp1 / rel).read_text()
            content2 = (tmp2 / rel).read_text()
            assert content1 == content2, f"File {rel} differs between runs"
