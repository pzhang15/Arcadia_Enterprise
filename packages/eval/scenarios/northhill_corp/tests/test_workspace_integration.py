import json

import pytest


@pytest.mark.asyncio
async def test_workspace_ls_root(l1_workspace):
    result = await l1_workspace.execute("ls /")
    assert result.exit_code == 0
    stdout = result.stdout.decode()
    for expected_dir in ("slack", "sheets", "gdocs", "tickets", "github",
                         "pagerduty", "datadog", "finance", "customers",
                         "compliance"):
        assert expected_dir in stdout, f"Missing mount: {expected_dir}"


@pytest.mark.asyncio
async def test_workspace_read_slack_users(l1_workspace):
    result = await l1_workspace.execute("ls /slack/users/")
    assert result.exit_code == 0
    stdout = result.stdout.decode()
    assert "U101" in stdout or "alex" in stdout


@pytest.mark.asyncio
async def test_workspace_read_ticket(l1_workspace):
    result = await l1_workspace.execute(
        "find /tickets/queues/it-helpdesk -name '*.json' -type f")
    assert result.exit_code == 0
    stdout = result.stdout.decode().strip()
    assert len(stdout) > 0, "No ticket files found"

    first_file = stdout.splitlines()[0].strip()
    result2 = await l1_workspace.execute(f"cat {first_file}")
    assert result2.exit_code == 0
    data = json.loads(result2.stdout.decode())
    assert "ticket_id" in data


@pytest.mark.asyncio
async def test_workspace_read_finance(l1_workspace):
    result = await l1_workspace.execute("ls /finance/")
    assert result.exit_code == 0
    stdout = result.stdout.decode()
    for expected in ("expenses", "purchase_orders", "invoices", "budgets"):
        assert expected in stdout, f"Missing finance dir: {expected}"


@pytest.mark.asyncio
async def test_workspace_read_budget(l1_workspace):
    result = await l1_workspace.execute("cat /finance/budgets/Q2_2026.json")
    assert result.exit_code == 0
    data = json.loads(result.stdout.decode())
    assert "departments" in data


@pytest.mark.asyncio
async def test_workspace_read_customers(l1_workspace):
    result = await l1_workspace.execute("ls /customers/accounts/")
    assert result.exit_code == 0
    stdout = result.stdout.decode()
    assert len(stdout.strip()) > 0, "No customer account files"


@pytest.mark.asyncio
async def test_workspace_read_compliance(l1_workspace):
    result = await l1_workspace.execute("ls /compliance/")
    assert result.exit_code == 0
    stdout = result.stdout.decode()
    for expected in ("contracts", "audits", "policies"):
        assert expected in stdout, f"Missing compliance dir: {expected}"


@pytest.mark.asyncio
async def test_workspace_write_and_read(l1_workspace):
    """Workspace should support write operations to the RAM root."""
    result = await l1_workspace.execute("echo test-output > /tmp_test.txt")
    assert result.exit_code == 0
    result2 = await l1_workspace.execute("cat /tmp_test.txt")
    assert result2.exit_code == 0
    assert "test-output" in result2.stdout.decode()


@pytest.mark.asyncio
async def test_workspace_cat_ticket_has_priority(l1_workspace):
    result = await l1_workspace.execute(
        "find /tickets/queues/it-helpdesk/open -name '*.json' -type f")
    assert result.exit_code == 0
    files = result.stdout.decode().strip().splitlines()
    assert len(files) >= 1, "No open IT tickets found"
    result2 = await l1_workspace.execute(f"cat {files[0].strip()}")
    assert result2.exit_code == 0
    data = json.loads(result2.stdout.decode())
    assert "priority" in data, "Ticket missing 'priority' field"


@pytest.mark.asyncio
async def test_workspace_pagerduty_accessible(l1_workspace):
    result = await l1_workspace.execute("ls /pagerduty/services/")
    assert result.exit_code == 0
    stdout = result.stdout.decode()
    assert len(stdout.strip()) > 0, "No PagerDuty service files"


@pytest.mark.asyncio
async def test_workspace_datadog_accessible(l1_workspace):
    result = await l1_workspace.execute("ls /datadog/metrics/platform-api/")
    assert result.exit_code == 0
    stdout = result.stdout.decode()
    assert len(stdout.strip()) > 0, "No Datadog metric files"
