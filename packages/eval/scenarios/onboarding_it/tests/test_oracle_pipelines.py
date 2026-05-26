"""Hand-written bash pipelines that solve each task end-to-end inside the
Mirage shell. Proves the corpus is solvable and pins the resource-touch
contract that the LLM-driven runs are scored against.

These tests do NOT call any LLM. They simulate what an "oracle agent"
would do, then assert the resulting output passes the same programmatic
gates from the task YAML."""
import asyncio

import pytest
from mirage_eval.scenario import ScenarioManifest


def _run(awaitable):
    return asyncio.get_event_loop().run_until_complete(awaitable)


@pytest.mark.asyncio
async def test_onboarding_status_oracle_pipeline_writes_required_file(
        l1_workspace):
    ws = l1_workspace
    cmds = [
        "cat /sheets/owned/2026-05-12_New_Hire_Tracker__SH101.gsheet.json "
        "| jq '[.sheets[0].data[0].rowData[] | "
        "[.values[].formattedValue]] | "
        ".[] | select(.[0] == \"Alex Rivera\")'",
        "ls /tickets/queues/it-helpdesk/open/",
        "for f in /tickets/queues/it-helpdesk/open/INC-100[124]*.json; "
        "do cat $f | jq -r '.ticket_id + \" \" + .subject'; done",
        "ls /slack/channels/onboarding__C302",
        "cat /slack/channels/onboarding__C302/2026-05-12/chat.jsonl",
        "ls /slack/dms/diana__D201",
        "cat /slack/dms/diana__D201/2026-05-11/chat.jsonl",
        "ls /slack/dms/sam__D202",
        "cat /slack/dms/sam__D202/2026-05-12/chat.jsonl",
    ]
    for cmd in cmds:
        result = await ws.execute(cmd)
        assert result.exit_code == 0, (
            f"oracle command failed: {cmd}\n"
            f"stderr={(result.stderr or b'').decode(errors='replace')}")
    body = (
        "# Onboarding status: Alex Rivera (Day 1: 2026-05-12)\n\n"
        "## Where they are in the playbook\n"
        "- Day 1 Complete = N. Equipment status = "
        "loaner_in_use_pending_shipment.\n"
        "- Manager: Marcus Johnson. Buddy: Jordan Kim.\n\n"
        "## What is blocked\n"
        "- INC-1001 (laptop): real device in transit; loaner active.\n"
        "- INC-1002 (AWS access): waiting on INC-1003 (Okta SSO) to land.\n"
        "- INC-1004 (GitHub org invite): pending acceptance.\n\n"
        "## Who owes what\n"
        "- Diana (HR): owns Day-1 checklist; latest DM 2026-05-12.\n"
        "- Sam (IT Lead): owns INC-1003 SSO sequencing; DM 2026-05-12.\n"
        "- Priya (IT Agent): owns INC-1001 and INC-1005 follow-up.\n")
    write_cmd = ("cat > /onboarding_status.md <<'EOF'\n" + body + "EOF")
    result = await ws.execute(write_cmd)
    assert result.exit_code == 0
    check = await ws.execute("cat /onboarding_status.md")
    assert check.exit_code == 0
    text = (check.stdout or b"").decode()
    manifest = ScenarioManifest.load("onboarding_it")
    task = manifest.load_task("onboarding_status")
    for needle in task.oracles.must_contain_in_file["/onboarding_status.md"]:
        assert needle in text, f"missing {needle!r} in oracle output"
    for banned in task.oracles.must_not_contain_in_file[
            "/onboarding_status.md"]:
        assert banned not in text, f"banned {banned!r} appeared"


@pytest.mark.asyncio
async def test_helpdesk_ticket_comment_add_writes_comment(l1_workspace):
    ws = l1_workspace
    add = await ws.execute(
        "helpdesk-ticket-comment-add --ticket INC-1004 "
        "--author U104 --body 'GitHub invite sent to alex.rivera@northhill.com'"
    )
    assert add.exit_code == 0, (add.stderr or b"").decode()
    check = await ws.execute(
        "cat /tickets/queues/it-helpdesk/open/INC-1004*.json | "
        "jq '.comments | length'")
    assert check.exit_code == 0
    n = int((check.stdout or b"").decode().strip())
    assert n >= 1


@pytest.mark.asyncio
async def test_helpdesk_ticket_transition_moves_file(l1_workspace):
    ws = l1_workspace
    txn = await ws.execute(
        "helpdesk-ticket-transition --ticket INC-1006 --status resolved")
    assert txn.exit_code == 0, (txn.stderr or b"").decode()
    open_listing = await ws.execute("ls /tickets/queues/it-helpdesk/open/")
    resolved_listing = await ws.execute(
        "ls /tickets/queues/it-helpdesk/resolved/")
    assert "INC-1006" not in (open_listing.stdout or b"").decode()
    assert "INC-1006" in (resolved_listing.stdout or b"").decode()
