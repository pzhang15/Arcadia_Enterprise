import json
from datetime import datetime, timezone
from pathlib import Path

from mirage.accessor.disk import DiskAccessor
from mirage.commands.config import command
from mirage.commands.spec.types import CommandSpec, OperandKind, Option
from mirage.io.types import ByteSource, IOResult
from mirage.resource.disk import DiskResource
from mirage.types import PathSpec

PROMPT = """\
{prefix}
  queues/<queue-name>/
    open/<ticket-id>.json
    in_progress/<ticket-id>.json
    resolved/<ticket-id>.json
  users/<username>/<ticket-id>.json    # flat view of tickets touching this user
  teams/<team-name>/<ticket-id>.json   # flat view of tickets owned by team
  draft/<ticket-id>_response.md        # write target for agent-drafted responses

  Filename: <ticket-id>__<short-slug>.json
    <ticket-id>   stable identifier, e.g. INC-1001 (sortable)
    <short-slug>  sanitized subject snippet (lowercase, _-separated)
  Always ls the queue subfolder first to discover exact filenames.

  Ticket JSON shape (generic ITSM, vendor-neutral):
    {{
      "ticket_id": "INC-1001",
      "subject": "...",
      "body": "...",
      "requester": {{"id": "U101", "name": "...", "email": "..."}},
      "assignee":  {{"id": "U104", "name": "..."}} | null,
      "queue":     "it-helpdesk",
      "status":    "open" | "in_progress" | "resolved",
      "priority":  "P1" | "P2" | "P3" | "P4",
      "created_at":"2026-05-11T14:02:11Z",
      "updated_at":"2026-05-12T09:14:32Z",
      "tags":      ["onboarding", "hardware"],
      "related_tickets": ["INC-1003"],
      "comments": [
        {{"author": "U104", "ts": "...", "body": "..."}}
      ]
    }}

  Useful jq paths:
    .ticket_id
    .status
    .priority
    .requester.name
    .assignee.id
    .comments[].body
    [.tags[]] | length

  Listing helpers (standard disk commands work as-is):
    ls   {prefix}/queues/it-helpdesk/open/
    cat  {prefix}/queues/it-helpdesk/open/INC-1001*.json
    grep -l Alex {prefix}/queues/it-helpdesk/open/*.json
    jq  '.requester.name' {prefix}/queues/it-helpdesk/open/INC-1001*.json"""

WRITE_PROMPT = """\
  Write commands (mutations are journaled into the ticket JSON in place):

    helpdesk-ticket-create --queue <q> --subject "..." --body "..." \\
      --requester <user-id> [--assignee <user-id>] [--priority P3] \\
      [--tags tag1,tag2]
        # Creates a new ticket under {prefix}/queues/<q>/open/.
        # Auto-assigns next ticket id (INC-NNNN). Returns the ticket JSON.

    helpdesk-ticket-comment-add --ticket INC-1001 --author <user-id> \\
      --body "..."
        # Appends a comment. Updates updated_at.

    helpdesk-ticket-transition --ticket INC-1001 --status in_progress|resolved
        # Moves the JSON file into the corresponding subfolder and
        # updates the .status field. Updates updated_at.

    helpdesk-ticket-assign --ticket INC-1001 --assignee <user-id> \\
      [--assignee-name "Full Name"]
        # Sets .assignee. Updates updated_at.

    helpdesk-ticket-set-priority --ticket INC-1001 --priority P1|P2|P3|P4

  IDs come from the filename prefix:
    {prefix}/queues/<q>/open/INC-1001__alex_laptop.json -> --ticket INC-1001

  Drafting a response (no side effect on the ticket itself):
    write to {prefix}/draft/<ticket-id>_response.md via standard shell
    redirection or `tee`. The draft folder is created on first write."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z")


def _find_ticket_path(root: Path, ticket_id: str) -> Path | None:
    queues = root / "queues"
    if not queues.exists():
        return None
    for queue_dir in queues.iterdir():
        if not queue_dir.is_dir():
            continue
        for status_dir_name in ("open", "in_progress", "resolved"):
            status_dir = queue_dir / status_dir_name
            if not status_dir.exists():
                continue
            for p in status_dir.iterdir():
                if p.is_file() and p.name.startswith(f"{ticket_id}__"):
                    return p
    return None


def _next_ticket_id(root: Path, queue: str) -> str:
    queue_dir = root / "queues" / queue
    seen: set[int] = set()
    if queue_dir.exists():
        for status_dir in queue_dir.iterdir():
            if not status_dir.is_dir():
                continue
            for p in status_dir.iterdir():
                if not p.is_file() or "__" not in p.name:
                    continue
                tid = p.name.split("__", 1)[0]
                if tid.startswith("INC-"):
                    try:
                        seen.add(int(tid.removeprefix("INC-")))
                    except ValueError:
                        pass
    nxt = max(seen) + 1 if seen else 1001
    return f"INC-{nxt:04d}"


def _slugify(text: str, max_len: int = 32) -> str:
    out = []
    for ch in text.lower().strip():
        if ch.isalnum():
            out.append(ch)
        elif ch in (" ", "-", "_"):
            out.append("_")
    slug = "".join(out)
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug[:max_len].strip("_") or "ticket"


def _load_ticket(path: Path) -> dict:
    return json.loads(path.read_text())


def _save_ticket(path: Path, ticket: dict) -> None:
    path.write_text(json.dumps(ticket, indent=2, ensure_ascii=False) + "\n")


_CREATE_SPEC = CommandSpec(options=(
    Option(long="--queue", value_kind=OperandKind.TEXT),
    Option(long="--subject", value_kind=OperandKind.TEXT),
    Option(long="--body", value_kind=OperandKind.TEXT),
    Option(long="--requester", value_kind=OperandKind.TEXT),
    Option(long="--assignee", value_kind=OperandKind.TEXT),
    Option(long="--priority", value_kind=OperandKind.TEXT),
    Option(long="--tags", value_kind=OperandKind.TEXT),
), )


@command("helpdesk-ticket-create",
         resource="disk",
         spec=_CREATE_SPEC,
         write=True)
async def helpdesk_ticket_create(
    accessor: DiskAccessor,
    paths: list[PathSpec],
    *texts: str,
    **extra: object,
) -> tuple[ByteSource | None, IOResult]:
    queue = str(extra.get("queue") or "")
    subject = str(extra.get("subject") or "")
    body = str(extra.get("body") or "")
    requester = str(extra.get("requester") or "")
    if not queue or not subject or not requester:
        raise ValueError(
            "--queue, --subject, and --requester are required")
    priority = str(extra.get("priority") or "P3").upper()
    if priority not in {"P1", "P2", "P3", "P4"}:
        raise ValueError(f"--priority must be P1..P4, got {priority!r}")
    assignee = extra.get("assignee")
    tags_raw = str(extra.get("tags") or "")
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
    root = accessor.root
    ticket_id = _next_ticket_id(root, queue)
    now = _now_iso()
    ticket = {
        "ticket_id": ticket_id,
        "subject": subject,
        "body": body,
        "requester": {"id": requester, "name": "", "email": ""},
        "assignee": ({"id": str(assignee), "name": ""} if assignee else None),
        "queue": queue,
        "status": "open",
        "priority": priority,
        "created_at": now,
        "updated_at": now,
        "tags": tags,
        "related_tickets": [],
        "comments": [],
    }
    queue_open = root / "queues" / queue / "open"
    queue_open.mkdir(parents=True, exist_ok=True)
    fname = f"{ticket_id}__{_slugify(subject)}.json"
    target = queue_open / fname
    _save_ticket(target, ticket)
    return json.dumps(ticket, ensure_ascii=False).encode(), IOResult()


_COMMENT_SPEC = CommandSpec(options=(
    Option(long="--ticket", value_kind=OperandKind.TEXT),
    Option(long="--author", value_kind=OperandKind.TEXT),
    Option(long="--body", value_kind=OperandKind.TEXT),
), )


@command("helpdesk-ticket-comment-add",
         resource="disk",
         spec=_COMMENT_SPEC,
         write=True)
async def helpdesk_ticket_comment_add(
    accessor: DiskAccessor,
    paths: list[PathSpec],
    *texts: str,
    **extra: object,
) -> tuple[ByteSource | None, IOResult]:
    ticket_id = str(extra.get("ticket") or "")
    author = str(extra.get("author") or "")
    body = str(extra.get("body") or "")
    if not ticket_id or not author or not body:
        raise ValueError("--ticket, --author, --body are required")
    target = _find_ticket_path(accessor.root, ticket_id)
    if target is None:
        raise FileNotFoundError(f"ticket {ticket_id!r} not found")
    ticket = _load_ticket(target)
    now = _now_iso()
    ticket.setdefault("comments", []).append({
        "author": author,
        "ts": now,
        "body": body,
    })
    ticket["updated_at"] = now
    _save_ticket(target, ticket)
    return json.dumps(ticket, ensure_ascii=False).encode(), IOResult()


_TRANSITION_SPEC = CommandSpec(options=(
    Option(long="--ticket", value_kind=OperandKind.TEXT),
    Option(long="--status", value_kind=OperandKind.TEXT),
), )


@command("helpdesk-ticket-transition",
         resource="disk",
         spec=_TRANSITION_SPEC,
         write=True)
async def helpdesk_ticket_transition(
    accessor: DiskAccessor,
    paths: list[PathSpec],
    *texts: str,
    **extra: object,
) -> tuple[ByteSource | None, IOResult]:
    ticket_id = str(extra.get("ticket") or "")
    new_status = str(extra.get("status") or "").lower()
    if not ticket_id:
        raise ValueError("--ticket is required")
    if new_status not in {"open", "in_progress", "resolved"}:
        raise ValueError(
            "--status must be open, in_progress, or resolved")
    src = _find_ticket_path(accessor.root, ticket_id)
    if src is None:
        raise FileNotFoundError(f"ticket {ticket_id!r} not found")
    ticket = _load_ticket(src)
    ticket["status"] = new_status
    ticket["updated_at"] = _now_iso()
    dst_dir = src.parent.parent / new_status
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    _save_ticket(dst, ticket)
    if dst != src:
        src.unlink()
    return json.dumps(ticket, ensure_ascii=False).encode(), IOResult()


_ASSIGN_SPEC = CommandSpec(options=(
    Option(long="--ticket", value_kind=OperandKind.TEXT),
    Option(long="--assignee", value_kind=OperandKind.TEXT),
    Option(long="--assignee-name", value_kind=OperandKind.TEXT),
), )


@command("helpdesk-ticket-assign",
         resource="disk",
         spec=_ASSIGN_SPEC,
         write=True)
async def helpdesk_ticket_assign(
    accessor: DiskAccessor,
    paths: list[PathSpec],
    *texts: str,
    **extra: object,
) -> tuple[ByteSource | None, IOResult]:
    ticket_id = str(extra.get("ticket") or "")
    assignee = str(extra.get("assignee") or "")
    name = str(extra.get("assignee-name") or extra.get("assignee_name") or "")
    if not ticket_id or not assignee:
        raise ValueError("--ticket and --assignee are required")
    target = _find_ticket_path(accessor.root, ticket_id)
    if target is None:
        raise FileNotFoundError(f"ticket {ticket_id!r} not found")
    ticket = _load_ticket(target)
    ticket["assignee"] = {"id": assignee, "name": name}
    ticket["updated_at"] = _now_iso()
    _save_ticket(target, ticket)
    return json.dumps(ticket, ensure_ascii=False).encode(), IOResult()


_PRIORITY_SPEC = CommandSpec(options=(
    Option(long="--ticket", value_kind=OperandKind.TEXT),
    Option(long="--priority", value_kind=OperandKind.TEXT),
), )


@command("helpdesk-ticket-set-priority",
         resource="disk",
         spec=_PRIORITY_SPEC,
         write=True)
async def helpdesk_ticket_set_priority(
    accessor: DiskAccessor,
    paths: list[PathSpec],
    *texts: str,
    **extra: object,
) -> tuple[ByteSource | None, IOResult]:
    ticket_id = str(extra.get("ticket") or "")
    priority = str(extra.get("priority") or "").upper()
    if not ticket_id:
        raise ValueError("--ticket is required")
    if priority not in {"P1", "P2", "P3", "P4"}:
        raise ValueError("--priority must be P1, P2, P3, or P4")
    target = _find_ticket_path(accessor.root, ticket_id)
    if target is None:
        raise FileNotFoundError(f"ticket {ticket_id!r} not found")
    ticket = _load_ticket(target)
    ticket["priority"] = priority
    ticket["updated_at"] = _now_iso()
    _save_ticket(target, ticket)
    return json.dumps(ticket, ensure_ascii=False).encode(), IOResult()


_HELPDESK_COMMANDS = (
    helpdesk_ticket_create,
    helpdesk_ticket_comment_add,
    helpdesk_ticket_transition,
    helpdesk_ticket_assign,
    helpdesk_ticket_set_priority,
)


class FakeTicketingResource(DiskResource):
    PROMPT: str = PROMPT
    WRITE_PROMPT: str = WRITE_PROMPT

    def __init__(self, root: str) -> None:
        super().__init__(root)
        for fn in _HELPDESK_COMMANDS:
            self.register(fn)
