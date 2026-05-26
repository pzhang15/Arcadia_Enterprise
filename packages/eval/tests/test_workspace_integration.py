import json
from pathlib import Path

import pytest
from scenarios.northhill_corp.mounts import build_l1_workspace

FIXTURE_ROOT = (Path(__file__).resolve().parent.parent / "scenarios" /
                "northhill_corp" / "fixture" / "disk")


def _stdout(result) -> str:
    out = result.stdout
    if isinstance(out, bytes):
        return out.decode()
    return out


@pytest.fixture(scope="module")
def workspace():
    if not FIXTURE_ROOT.exists():
        pytest.skip("northhill_corp fixture not seeded")
    return build_l1_workspace(disk_root=FIXTURE_ROOT)


@pytest.mark.asyncio
async def test_ls_root_shows_all_mounts(workspace):
    result = await workspace.execute("ls /")
    stdout = _stdout(result)
    for mount in ("slack", "sheets", "gdocs", "tickets", "github",
                  "pagerduty", "datadog", "finance", "customers",
                  "compliance", "database", "s3"):
        assert mount in stdout, f"Mount /{mount} not in ls / output"


@pytest.mark.asyncio
async def test_ls_database_tables(workspace):
    result = await workspace.execute("ls /database/tables/")
    stdout = _stdout(result)
    for table in ("users", "events", "subscriptions", "invoices"):
        assert table in stdout


@pytest.mark.asyncio
async def test_cat_database_schema(workspace):
    result = await workspace.execute("cat /database/tables/users/schema.json")
    data = json.loads(_stdout(result))
    assert data["table"] == "users"
    assert len(data["columns"]) > 0
    col_names = {c["name"] for c in data["columns"]}
    assert "id" in col_names or "user_id" in col_names


@pytest.mark.asyncio
async def test_cat_database_data_jsonl(workspace):
    result = await workspace.execute(
        "cat /database/tables/subscriptions/data.jsonl")
    lines = [l for l in _stdout(result).splitlines() if l.strip()]
    assert len(lines) > 0
    first_row = json.loads(lines[0])
    assert isinstance(first_row, dict)


@pytest.mark.asyncio
async def test_ls_s3_bucket(workspace):
    result = await workspace.execute("ls /s3/northhill-data/")
    stdout = _stdout(result)
    for subdir in ("logs", "exports", "artifacts"):
        assert subdir in stdout


@pytest.mark.asyncio
async def test_cat_s3_log_file(workspace):
    result = await workspace.execute(
        "ls /s3/northhill-data/logs/platform-api/2026/05/")
    stdout = _stdout(result)
    assert stdout.strip()
    day_dirs = stdout.strip().split()
    assert len(day_dirs) > 0
    first_day = day_dirs[0].strip("/")
    log_result = await workspace.execute(
        f"ls /s3/northhill-data/logs/platform-api/2026/05/{first_day}/")
    assert "app.log" in _stdout(log_result)


@pytest.mark.asyncio
async def test_cat_s3_csv_export(workspace):
    result = await workspace.execute(
        "ls /s3/northhill-data/exports/monthly/")
    stdout = _stdout(result)
    assert ".csv" in stdout


@pytest.mark.asyncio
async def test_ls_tickets_queues(workspace):
    result = await workspace.execute("ls /tickets/queues/")
    stdout = _stdout(result)
    assert "it-helpdesk" in stdout
    assert "customer-support" in stdout


@pytest.mark.asyncio
async def test_cat_ticket_json(workspace):
    result = await workspace.execute("ls /tickets/queues/it-helpdesk/open/")
    files = _stdout(result).strip().split()
    assert len(files) > 0
    first_ticket = files[0]
    cat_result = await workspace.execute(
        f"cat /tickets/queues/it-helpdesk/open/{first_ticket}")
    data = json.loads(_stdout(cat_result))
    assert "ticket_id" in data
    assert data["status"] == "open"
    assert "requester" in data


@pytest.mark.asyncio
async def test_ls_finance_expenses(workspace):
    result = await workspace.execute("ls /finance/expenses/pending/")
    stdout = _stdout(result)
    assert "EXP-" in stdout


@pytest.mark.asyncio
async def test_cat_finance_expense(workspace):
    result = await workspace.execute("ls /finance/expenses/pending/")
    files = _stdout(result).strip().split()
    first = files[0]
    cat_result = await workspace.execute(f"cat /finance/expenses/pending/{first}")
    data = json.loads(_stdout(cat_result))
    assert "expense_id" in data
    assert "amount" in data
    assert isinstance(data["amount"], (int, float))


@pytest.mark.asyncio
async def test_ls_customers_accounts(workspace):
    result = await workspace.execute("ls /customers/accounts/")
    stdout = _stdout(result)
    assert "ACCT-" in stdout


@pytest.mark.asyncio
async def test_cat_customer_account(workspace):
    result = await workspace.execute("ls /customers/accounts/")
    files = _stdout(result).strip().split()
    first = files[0]
    cat_result = await workspace.execute(f"cat /customers/accounts/{first}")
    data = json.loads(_stdout(cat_result))
    assert "account_id" in data
    assert "health_score" in data
    assert "company_name" in data


@pytest.mark.asyncio
async def test_ls_compliance_audits(workspace):
    result = await workspace.execute("ls /compliance/audits/")
    stdout = _stdout(result)
    assert "AUDIT-" in stdout


@pytest.mark.asyncio
async def test_cat_compliance_audit(workspace):
    result = await workspace.execute("ls /compliance/audits/")
    files = _stdout(result).strip().split()
    first = files[0]
    cat_result = await workspace.execute(f"cat /compliance/audits/{first}")
    data = json.loads(_stdout(cat_result))
    assert "audit_id" in data
    assert "framework" in data
    assert "checklist" in data


@pytest.mark.asyncio
async def test_ls_pagerduty_incidents(workspace):
    result = await workspace.execute("ls /pagerduty/incidents/")
    stdout = _stdout(result)
    assert "triggered" in stdout or "resolved" in stdout


@pytest.mark.asyncio
async def test_ls_datadog_logs(workspace):
    result = await workspace.execute("ls /datadog/logs/")
    stdout = _stdout(result)
    assert "platform-api" in stdout


@pytest.mark.asyncio
async def test_ls_github_repos(workspace):
    result = await workspace.execute("ls /github/repos/")
    stdout = _stdout(result)
    assert "northhill" in stdout


@pytest.mark.asyncio
async def test_ls_slack_channels(workspace):
    result = await workspace.execute("ls /slack/channels/")
    stdout = _stdout(result)
    assert len(stdout.strip().split()) >= 5


@pytest.mark.asyncio
async def test_cross_reference_customer_to_escalation(workspace):
    """Verify customer accounts can be cross-referenced with escalations."""
    acct_result = await workspace.execute("ls /customers/accounts/")
    acct_files = _stdout(acct_result).strip().split()
    first_acct_file = acct_files[0]
    acct_data = json.loads(
        _stdout(await workspace.execute(
            f"cat /customers/accounts/{first_acct_file}")))
    acct_id = acct_data["account_id"]

    esc_result = await workspace.execute("ls /customers/escalations/")
    esc_files = _stdout(esc_result).strip().split()
    found_link = False
    for esc_file in esc_files:
        esc_data = json.loads(
            _stdout(await workspace.execute(
                f"cat /customers/escalations/{esc_file}")))
        if esc_data.get("account_id") == acct_id:
            found_link = True
            break
    assert found_link or len(esc_files) == 0


@pytest.mark.asyncio
async def test_cross_reference_database_subscriptions_to_accounts(workspace):
    """Verify database subscription data references valid account IDs."""
    sub_result = await workspace.execute(
        "cat /database/tables/subscriptions/data.jsonl")
    lines = [l for l in _stdout(sub_result).splitlines() if l.strip()]
    assert len(lines) > 0

    acct_result = await workspace.execute("ls /customers/accounts/")
    acct_files = _stdout(acct_result).strip().split()
    acct_ids = set()
    for f in acct_files:
        data = json.loads(
            _stdout(await workspace.execute(f"cat /customers/accounts/{f}")))
        acct_ids.add(data["account_id"])

    for line in lines[:5]:
        row = json.loads(line)
        if "account_id" in row:
            assert row["account_id"] in acct_ids, (
                f"Subscription references unknown account {row['account_id']}")


@pytest.mark.asyncio
async def test_write_to_ram_root(workspace):
    """Verify the RAM root mount is writable."""
    result = await workspace.execute(
        'echo "test content" | tee /test_output.md')
    assert result.exit_code == 0
    cat_result = await workspace.execute("cat /test_output.md")
    assert "test content" in _stdout(cat_result)


@pytest.mark.asyncio
async def test_jq_on_database_schema(workspace):
    """Test jq-style queries work on database schemas."""
    result = await workspace.execute(
        "jq '.columns[].name' /database/tables/users/schema.json")
    assert result.exit_code == 0
    assert len(_stdout(result).strip()) > 0
