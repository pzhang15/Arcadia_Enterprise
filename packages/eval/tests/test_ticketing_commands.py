import json
from pathlib import Path

import pytest
from mirage import MountMode, Workspace
from mirage_eval.fixtures import FakeTicketingResource


def _stdout(result) -> str:
    out = result.stdout
    if isinstance(out, bytes):
        return out.decode()
    return out


@pytest.fixture
def ticket_workspace(tmp_path: Path) -> Workspace:
    queue_dir = tmp_path / "queues" / "it-helpdesk" / "open"
    queue_dir.mkdir(parents=True)
    ticket = {
        "ticket_id": "INC-1001",
        "subject": "Laptop not arrived",
        "body": "My laptop hasn't arrived yet.",
        "requester": {
            "id": "U101",
            "name": "Alex Rivera",
            "email": "alex@northhill.com"
        },
        "assignee": None,
        "queue": "it-helpdesk",
        "status": "open",
        "priority": "P2",
        "created_at": "2026-05-11T14:02:11Z",
        "updated_at": "2026-05-12T09:14:32Z",
        "tags": ["onboarding", "hardware"],
        "related_tickets": [],
        "comments": [],
    }
    fname = "INC-1001__laptop_not_arrived.json"
    (queue_dir / fname).write_text(json.dumps(ticket, indent=2))

    resource = FakeTicketingResource(str(tmp_path))
    return Workspace(
        {"/tickets": (resource, MountMode.WRITE)},
        mode=MountMode.WRITE,
    )


@pytest.mark.asyncio
async def test_create_ticket(ticket_workspace: Workspace):
    result = await ticket_workspace.execute(
        'helpdesk-ticket-create --queue it-helpdesk '
        '--subject "VPN not working" --body "Cannot connect to VPN" '
        '--requester U105 --priority P2 --tags vpn,network')
    assert result.exit_code == 0
    data = json.loads(_stdout(result))
    assert data["ticket_id"] == "INC-1002"
    assert data["subject"] == "VPN not working"
    assert data["requester"]["id"] == "U105"
    assert data["priority"] == "P2"
    assert data["status"] == "open"
    assert "vpn" in data["tags"]
    assert "network" in data["tags"]


@pytest.mark.asyncio
async def test_create_ticket_auto_increments_id(ticket_workspace: Workspace):
    await ticket_workspace.execute(
        'helpdesk-ticket-create --queue it-helpdesk '
        '--subject "Issue A" --body "body" --requester U101')
    result = await ticket_workspace.execute(
        'helpdesk-ticket-create --queue it-helpdesk '
        '--subject "Issue B" --body "body" --requester U102')
    data = json.loads(_stdout(result))
    assert data["ticket_id"] == "INC-1003"


@pytest.mark.asyncio
async def test_create_ticket_requires_fields(ticket_workspace: Workspace):
    result = await ticket_workspace.execute(
        'helpdesk-ticket-create --queue it-helpdesk --subject "No requester"'
        ' --body "body"')
    assert result.exit_code != 0


@pytest.mark.asyncio
async def test_add_comment(ticket_workspace: Workspace):
    result = await ticket_workspace.execute(
        'helpdesk-ticket-comment-add --ticket INC-1001 '
        '--author U104 --body "Looking into this now."')
    assert result.exit_code == 0
    data = json.loads(_stdout(result))
    assert len(data["comments"]) == 1
    assert data["comments"][0]["author"] == "U104"
    assert data["comments"][0]["body"] == "Looking into this now."
    assert data["updated_at"] != "2026-05-12T09:14:32Z"


@pytest.mark.asyncio
async def test_add_multiple_comments(ticket_workspace: Workspace):
    await ticket_workspace.execute(
        'helpdesk-ticket-comment-add --ticket INC-1001 '
        '--author U104 --body "First comment"')
    result = await ticket_workspace.execute(
        'helpdesk-ticket-comment-add --ticket INC-1001 '
        '--author U103 --body "Second comment"')
    data = json.loads(_stdout(result))
    assert len(data["comments"]) == 2


@pytest.mark.asyncio
async def test_comment_on_nonexistent_ticket(ticket_workspace: Workspace):
    result = await ticket_workspace.execute(
        'helpdesk-ticket-comment-add --ticket INC-9999 '
        '--author U104 --body "ghost ticket"')
    assert result.exit_code != 0


@pytest.mark.asyncio
async def test_transition_to_in_progress(ticket_workspace: Workspace):
    result = await ticket_workspace.execute(
        'helpdesk-ticket-transition --ticket INC-1001 --status in_progress')
    assert result.exit_code == 0
    data = json.loads(_stdout(result))
    assert data["status"] == "in_progress"

    ls_result = await ticket_workspace.execute(
        "ls /tickets/queues/it-helpdesk/in_progress/")
    assert "INC-1001" in _stdout(ls_result)

    ls_open = await ticket_workspace.execute(
        "ls /tickets/queues/it-helpdesk/open/")
    assert "INC-1001" not in _stdout(ls_open)


@pytest.mark.asyncio
async def test_transition_to_resolved(ticket_workspace: Workspace):
    await ticket_workspace.execute(
        'helpdesk-ticket-transition --ticket INC-1001 --status in_progress')
    result = await ticket_workspace.execute(
        'helpdesk-ticket-transition --ticket INC-1001 --status resolved')
    assert result.exit_code == 0
    data = json.loads(_stdout(result))
    assert data["status"] == "resolved"

    ls_result = await ticket_workspace.execute(
        "ls /tickets/queues/it-helpdesk/resolved/")
    assert "INC-1001" in _stdout(ls_result)


@pytest.mark.asyncio
async def test_transition_invalid_status(ticket_workspace: Workspace):
    result = await ticket_workspace.execute(
        'helpdesk-ticket-transition --ticket INC-1001 --status deleted')
    assert result.exit_code != 0


@pytest.mark.asyncio
async def test_assign_ticket(ticket_workspace: Workspace):
    result = await ticket_workspace.execute(
        'helpdesk-ticket-assign --ticket INC-1001 --assignee U104 '
        '--assignee-name "Priya Patel"')
    assert result.exit_code == 0
    data = json.loads(_stdout(result))
    assert data["assignee"]["id"] == "U104"
    assert data["assignee"]["name"] == "Priya Patel"


@pytest.mark.asyncio
async def test_assign_nonexistent_ticket(ticket_workspace: Workspace):
    result = await ticket_workspace.execute(
        'helpdesk-ticket-assign --ticket INC-9999 --assignee U104')
    assert result.exit_code != 0


@pytest.mark.asyncio
async def test_set_priority(ticket_workspace: Workspace):
    result = await ticket_workspace.execute(
        'helpdesk-ticket-set-priority --ticket INC-1001 --priority P1')
    assert result.exit_code == 0
    data = json.loads(_stdout(result))
    assert data["priority"] == "P1"


@pytest.mark.asyncio
async def test_set_invalid_priority(ticket_workspace: Workspace):
    result = await ticket_workspace.execute(
        'helpdesk-ticket-set-priority --ticket INC-1001 --priority P5')
    assert result.exit_code != 0


@pytest.mark.asyncio
async def test_full_ticket_lifecycle(ticket_workspace: Workspace):
    """End-to-end: create -> assign -> comment -> transition -> resolve."""
    create_result = await ticket_workspace.execute(
        'helpdesk-ticket-create --queue it-helpdesk '
        '--subject "Server issue" --body "Server is down" '
        '--requester U201 --priority P1 --tags production,urgent')
    create_data = json.loads(_stdout(create_result))
    ticket_id = create_data["ticket_id"]
    assert ticket_id == "INC-1002"

    assign_result = await ticket_workspace.execute(
        f'helpdesk-ticket-assign --ticket {ticket_id} --assignee U212 '
        f'--assignee-name "Bob Martinez"')
    assert assign_result.exit_code == 0

    comment_result = await ticket_workspace.execute(
        f'helpdesk-ticket-comment-add --ticket {ticket_id} '
        f'--author U212 --body "Investigating the issue now."')
    assert comment_result.exit_code == 0

    transition_result = await ticket_workspace.execute(
        f'helpdesk-ticket-transition --ticket {ticket_id} '
        f'--status in_progress')
    assert transition_result.exit_code == 0

    comment2_result = await ticket_workspace.execute(
        f'helpdesk-ticket-comment-add --ticket {ticket_id} '
        f'--author U212 --body "Resolved by restarting the service."')
    assert comment2_result.exit_code == 0

    resolve_result = await ticket_workspace.execute(
        f'helpdesk-ticket-transition --ticket {ticket_id} --status resolved')
    resolve_data = json.loads(_stdout(resolve_result))
    assert resolve_data["status"] == "resolved"
    assert len(resolve_data["comments"]) == 2
    assert resolve_data["assignee"]["id"] == "U212"
