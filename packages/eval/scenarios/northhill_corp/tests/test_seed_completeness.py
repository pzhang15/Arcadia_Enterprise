import json
from pathlib import Path


def _count_files(d: Path, suffix: str = ".json") -> int:
    if not d.exists():
        return 0
    return sum(1 for _ in d.rglob(f"*{suffix}"))


def test_slack_users_seeded(disk_root):
    users_dir = disk_root / "slack" / "users"
    assert users_dir.exists(), "slack/users directory missing"
    user_files = list(users_dir.glob("*.json"))
    assert len(
        user_files) >= 10, f"Expected >=10 user files, got {len(user_files)}"
    sample = json.loads(user_files[0].read_text())
    assert "id" in sample
    assert "name" in sample


def test_slack_channels_seeded(disk_root):
    channels_dir = disk_root / "slack" / "channels"
    assert channels_dir.exists(), "slack/channels directory missing"
    channel_dirs = [d for d in channels_dir.iterdir() if d.is_dir()]
    assert len(channel_dirs) >= 1, "No channel subdirectories found"


def test_sheets_seeded(disk_root):
    sheets_dir = disk_root / "sheets" / "owned"
    assert sheets_dir.exists(), "sheets/owned directory missing"
    sheet_files = list(sheets_dir.glob("*.json"))
    assert len(
        sheet_files) >= 3, f"Expected >=3 sheets, got {len(sheet_files)}"
    sample = json.loads(sheet_files[0].read_text())
    has_id = "spreadsheetId" in sample or "spreadsheet_id" in sample
    has_title = "properties" in sample or "title" in sample
    assert has_id or has_title, (
        f"Sheet missing expected keys: {list(sample.keys())}")


def test_gdocs_seeded(disk_root):
    gdocs_dir = disk_root / "gdocs" / "owned"
    assert gdocs_dir.exists(), "gdocs/owned directory missing"
    doc_files = list(gdocs_dir.glob("*.json"))
    assert len(doc_files) >= 5, f"Expected >=5 gdocs, got {len(doc_files)}"


def test_tickets_it_helpdesk_seeded(disk_root):
    helpdesk = disk_root / "tickets" / "queues" / "it-helpdesk"
    assert helpdesk.exists(), "tickets/queues/it-helpdesk missing"
    for status in ("open", "in_progress", "resolved"):
        status_dir = helpdesk / status
        assert status_dir.exists(), f"it-helpdesk/{status} missing"
        files = list(status_dir.glob("*.json"))
        assert len(files) >= 1, f"No tickets in it-helpdesk/{status}"


def test_tickets_customer_support_seeded(disk_root):
    cs = disk_root / "tickets" / "queues" / "customer-support"
    assert cs.exists(), "tickets/queues/customer-support missing"
    total = _count_files(cs)
    assert total >= 3, f"Expected >=3 customer support tickets, got {total}"


def test_tickets_legal_seeded(disk_root):
    legal = disk_root / "tickets" / "queues" / "legal"
    assert legal.exists(), "tickets/queues/legal missing"
    total = _count_files(legal)
    assert total >= 1, f"Expected >=1 legal tickets, got {total}"


def test_finance_expenses_seeded(disk_root):
    expenses = disk_root / "finance" / "expenses"
    assert expenses.exists(), "finance/expenses missing"
    total = _count_files(expenses)
    assert total >= 3, f"Expected >=3 expense files, got {total}"
    for status in ("pending", "approved", "rejected"):
        d = expenses / status
        if d.exists():
            for f in d.glob("*.json"):
                data = json.loads(f.read_text())
                assert "expense_id" in data, f"Missing expense_id in {f.name}"
                assert "amount" in data, f"Missing amount in {f.name}"
                assert "status" in data, f"Missing status in {f.name}"


def test_finance_purchase_orders_seeded(disk_root):
    pos = disk_root / "finance" / "purchase_orders"
    assert pos.exists(), "finance/purchase_orders missing"
    total = _count_files(pos)
    assert total >= 2, f"Expected >=2 PO files, got {total}"


def test_finance_invoices_seeded(disk_root):
    invoices = disk_root / "finance" / "invoices"
    assert invoices.exists(), "finance/invoices missing"
    total = _count_files(invoices)
    assert total >= 2, f"Expected >=2 invoice files, got {total}"


def test_finance_budgets_seeded(disk_root):
    budget_file = disk_root / "finance" / "budgets" / "Q2_2026.json"
    assert budget_file.exists(), "finance/budgets/Q2_2026.json missing"
    data = json.loads(budget_file.read_text())
    assert "departments" in data, "Budget missing 'departments' key"
    assert len(data["departments"]) >= 1, "No departments in budget"


def test_customers_accounts_seeded(disk_root):
    accounts = disk_root / "customers" / "accounts"
    assert accounts.exists(), "customers/accounts missing"
    files = list(accounts.glob("*.json"))
    assert len(files) >= 3, f"Expected >=3 accounts, got {len(files)}"
    sample = json.loads(files[0].read_text())
    assert "account_id" in sample
    assert "health_score" in sample


def test_customers_escalations_seeded(disk_root):
    escalations = disk_root / "customers" / "escalations"
    assert escalations.exists(), "customers/escalations missing"
    files = list(escalations.glob("*.json"))
    assert len(files) >= 2, f"Expected >=2 escalations, got {len(files)}"


def test_compliance_contracts_seeded(disk_root):
    contracts = disk_root / "compliance" / "contracts"
    assert contracts.exists(), "compliance/contracts missing"
    total = _count_files(contracts)
    assert total >= 3, f"Expected >=3 contracts, got {total}"


def test_compliance_audits_seeded(disk_root):
    audits = disk_root / "compliance" / "audits"
    assert audits.exists(), "compliance/audits missing"
    files = list(audits.glob("*.json"))
    assert len(files) >= 1, f"Expected >=1 audit, got {len(files)}"


def test_compliance_policies_seeded(disk_root):
    policies = disk_root / "compliance" / "policies"
    assert policies.exists(), "compliance/policies missing"
    files = list(policies.glob("*.json"))
    assert len(files) >= 1, f"Expected >=1 policy, got {len(files)}"


def test_engineering_github_seeded(disk_root):
    gh = disk_root / "github" / "repos" / "northhill" / "platform-api"
    assert gh.exists(), "github/repos/northhill/platform-api missing"
    for sub in ("deployments", "commits", "pulls"):
        d = gh / sub
        assert d.exists(), f"github .../platform-api/{sub} missing"
        files = list(d.glob("*.json"))
        assert len(files) >= 1, f"No files in {sub}"


def test_engineering_pagerduty_seeded(disk_root):
    pd = disk_root / "pagerduty"
    assert pd.exists(), "pagerduty missing"
    services = list((pd / "services").glob("*.json"))
    assert len(services) >= 1, "No PagerDuty services"
    incidents = _count_files(pd / "incidents")
    assert incidents >= 1, "No PagerDuty incidents"


def test_engineering_datadog_seeded(disk_root):
    dd = disk_root / "datadog"
    assert dd.exists(), "datadog missing"
    metrics = disk_root / "datadog" / "metrics" / "platform-api"
    assert metrics.exists(), "datadog/metrics/platform-api missing"
    files = list(metrics.glob("*.json"))
    assert len(files) >= 1, "No Datadog metric files"


def test_generated_employees_present(disk_root):
    """Slack users should include generated employees."""
    users_dir = disk_root / "slack" / "users"
    user_files = list(users_dir.glob("*.json"))
    assert len(user_files) >= 100, (
        f"Expected >=100 user profiles (26 hand-crafted + ~90 generated), "
        f"got {len(user_files)}")


def test_generated_customers_present(disk_root):
    """Customer accounts should include hand-crafted + generated."""
    accounts = disk_root / "customers" / "accounts"
    files = list(accounts.glob("*.json"))
    assert len(files) >= 40, (
        f"Expected >=40 customer accounts (6 hand-crafted + ~45 generated), "
        f"got {len(files)}")


def test_slack_ambient_messages_added(disk_root):
    """Channels should have more messages than the hand-crafted minimum."""
    ch_dir = disk_root / "slack" / "channels" / "platform-team__C303"
    total_messages = 0
    for jsonl in ch_dir.rglob("chat.jsonl"):
        total_messages += len(jsonl.read_text().strip().split("\n"))
    assert total_messages >= 10, (
        f"Expected >=10 messages in platform-team "
        f"(ambient + hand-crafted), got {total_messages}")


def test_database_tables_seeded(disk_root):
    """All 4 database tables exist with schema, data, and stats."""
    db = disk_root / "database" / "tables"
    assert db.exists(), "database/tables missing"
    for table in ("users", "events", "subscriptions", "invoices"):
        table_dir = db / table
        assert table_dir.exists(), f"database/tables/{table} missing"
        assert (table_dir /
                "schema.json").exists(), (f"{table}/schema.json missing")
        assert (table_dir /
                "data.jsonl").exists(), (f"{table}/data.jsonl missing")
        assert (table_dir /
                "stats.json").exists(), (f"{table}/stats.json missing")
        schema = json.loads((table_dir / "schema.json").read_text())
        assert schema["table"] == table
        assert len(schema["columns"]) >= 3


def test_database_cross_references(disk_root):
    """Account IDs in database must reference customer accounts."""
    accounts_dir = disk_root / "customers" / "accounts"
    account_ids = set()
    for f in accounts_dir.glob("*.json"):
        data = json.loads(f.read_text())
        account_ids.add(data["account_id"])

    subs_file = (disk_root / "database" / "tables" / "subscriptions" /
                 "data.jsonl")
    for line in subs_file.read_text().strip().split("\n"):
        row = json.loads(line)
        assert row["account_id"] in account_ids, (
            f"Subscription references unknown account {row['account_id']}")


def test_database_row_counts(disk_root):
    """Database tables should have the expected number of rows."""
    db = disk_root / "database" / "tables"
    users_lines = len(
        (db / "users" / "data.jsonl").read_text().strip().split("\n"))
    assert users_lines == 500, f"Expected 500 user rows, got {users_lines}"
    events_lines = len(
        (db / "events" / "data.jsonl").read_text().strip().split("\n"))
    assert events_lines == 5000, (
        f"Expected 5000 event rows, got {events_lines}")
    inv_lines = len(
        (db / "invoices" / "data.jsonl").read_text().strip().split("\n"))
    assert inv_lines == 200, f"Expected 200 invoice rows, got {inv_lines}"


def test_s3_seeded(disk_root):
    """S3 bucket structure should exist with logs, artifacts, and exports."""
    s3 = disk_root / "s3" / "northhill-data"
    assert s3.exists(), "s3/northhill-data missing"
    assert (s3 / "logs" / "platform-api").exists(), "logs/platform-api missing"
    assert (s3 / "artifacts" /
            "deployments").exists(), ("artifacts/deployments missing")
    assert (s3 / "exports" / "monthly").exists(), "exports/monthly missing"
    assert (s3 / "backups" / "db").exists(), "backups/db missing"
    assert (s3 / "reports" /
            "quarterly").exists(), ("reports/quarterly missing")


def test_s3_build_log_cross_references(disk_root):
    """Build log should reference the incident commit and deployer."""
    build_log = (disk_root / "s3" / "northhill-data" / "artifacts" /
                 "deployments" / "v3.18.7" / "build.log")
    assert build_log.exists(), "v3.18.7/build.log missing"
    content = build_log.read_text()
    assert "f3a1b2c8" in content, "Build log missing commit SHA f3a1b2c8"
    assert "frank.osei" in content, "Build log missing deployer frank.osei"
    assert "connectionPoolSize" in content, (
        "Build log missing connectionPoolSize config change")
    assert "d4e5f6" in content, "Build log missing deployment ID d4e5f6"


def test_s3_daily_logs_exist(disk_root):
    """Daily app logs should exist for May 10-15."""
    for day in range(10, 16):
        log_file = (disk_root / "s3" / "northhill-data" / "logs" /
                    "platform-api" / "2026" / "05" / f"{day:02d}" / "app.log")
        assert log_file.exists(), f"Missing app.log for May {day}"
        lines = log_file.read_text().strip().split("\n")
        assert len(lines) >= 50, (
            f"Expected >=50 log lines for May {day}, got {len(lines)}")


def test_seed_is_idempotent(disk_root):
    """Re-seeding with clean=True should produce the same files."""
    from scenarios.northhill_corp.seed import main as seed_main
    files_before = sorted(
        str(p.relative_to(disk_root)) for p in disk_root.rglob("*.json"))
    seed_main(disk_root, clean=True)
    files_after = sorted(
        str(p.relative_to(disk_root)) for p in disk_root.rglob("*.json"))
    assert files_before == files_after, "Seed is not idempotent"


def test_all_json_files_are_valid(disk_root):
    """Every .json file should be valid JSON."""
    broken = []
    for f in disk_root.rglob("*.json"):
        try:
            json.loads(f.read_text())
        except json.JSONDecodeError:
            broken.append(str(f.relative_to(disk_root)))
    assert not broken, f"Invalid JSON files: {broken}"


def test_total_file_count(disk_root):
    """Expanded scenario should produce >300 files."""
    total = sum(1 for _ in disk_root.rglob("*") if _.is_file())
    assert total > 300, f"Expected >300 files, got {total}"
