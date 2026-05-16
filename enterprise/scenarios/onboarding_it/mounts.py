import os
from pathlib import Path

from mirage import MountMode, RAMResource, Workspace

from mirage_eval.fixtures import (FakeGDocsResource, FakeGSheetsResource,
                                  FakeSlackResource, FakeTicketingResource)

DEFAULT_DISK_ROOT = (Path(__file__).resolve().parent / "fixture"
                     / "disk").resolve()


def build_l1_workspace(
    disk_root: str | Path | None = None,
    *,
    agent_id: str = "mirage-eval",
    session_id: str = "default",
) -> Workspace:
    """Construct an L1 (synthetic, offline) workspace for this scenario.

    Args:
        disk_root (str | Path | None): Filesystem root containing the seeded
            slack/sheets/gdocs/tickets subtrees. Defaults to
            ``enterprise/scenarios/onboarding_it/fixture/disk/``.
        agent_id (str): Agent identifier for session isolation.
        session_id (str): Session identifier; used in
            ``/.sessions/<date>/<session_id>.jsonl``.
    """
    root = Path(disk_root or DEFAULT_DISK_ROOT).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(
            f"disk root {root} not found - run `mirage-eval seed --scenario "
            f"onboarding_it` first")
    return Workspace(
        {
            "/": (RAMResource(), MountMode.WRITE),
            "/slack": (FakeSlackResource(str(root / "slack")), MountMode.READ),
            "/sheets": (FakeGSheetsResource(str(root / "sheets")),
                        MountMode.READ),
            "/gdocs": (FakeGDocsResource(str(root / "gdocs")), MountMode.READ),
            "/tickets": (FakeTicketingResource(str(root / "tickets")),
                         MountMode.WRITE),
        },
        mode=MountMode.WRITE,
        agent_id=agent_id,
        session_id=session_id,
    )


def build_l2_workspace(
    *,
    agent_id: str = "mirage-eval",
    session_id: str = "default",
    disk_root: str | Path | None = None,
) -> Workspace:
    """Construct an L2 (real Slack + real Google) workspace.

    Tickets remain disk-backed via ``FakeTicketingResource`` in v1, so only
    Slack and Google require real credentials. See
    ``scenarios/onboarding_it/README.md`` for the one-time setup.

    Args:
        agent_id (str): Agent identifier for session isolation.
        session_id (str): Session identifier.
        disk_root (str | Path | None): Filesystem root for the
            disk-backed ticket queue (defaults to the L1 root).
    """
    from mirage.resource.gdocs import GDocsConfig, GDocsResource
    from mirage.resource.gsheets import GSheetsConfig, GSheetsResource
    from mirage.resource.slack import SlackConfig, SlackResource

    google_kwargs = dict(
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
    )
    slack = SlackResource(config=SlackConfig(
        token=os.environ["SLACK_BOT_TOKEN"],
        search_token=os.environ.get("SLACK_USER_TOKEN") or None,
    ))
    sheets = GSheetsResource(config=GSheetsConfig(**google_kwargs))
    docs = GDocsResource(config=GDocsConfig(**google_kwargs))
    root = Path(disk_root or DEFAULT_DISK_ROOT).expanduser().resolve()
    tickets_root = root / "tickets"
    if not tickets_root.exists():
        raise FileNotFoundError(
            f"ticket root {tickets_root} not found - run "
            f"`mirage-eval seed --scenario onboarding_it` first")
    return Workspace(
        {
            "/": (RAMResource(), MountMode.WRITE),
            "/slack": (slack, MountMode.READ),
            "/sheets": (sheets, MountMode.READ),
            "/gdocs": (docs, MountMode.READ),
            "/tickets": (FakeTicketingResource(str(tickets_root)),
                         MountMode.WRITE),
        },
        mode=MountMode.WRITE,
        agent_id=agent_id,
        session_id=session_id,
    )
