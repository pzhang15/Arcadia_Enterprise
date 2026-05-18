from pathlib import Path

from mirage_eval.fixtures import (FakeDatadogResource, FakeGDocsResource,
                                  FakeGitHubResource, FakeGSheetsResource,
                                  FakePagerDutyResource, FakeSlackResource,
                                  FakeTicketingResource)

from mirage import MountMode, RAMResource, Workspace
from mirage.resource.disk import DiskResource

DEFAULT_DISK_ROOT = (Path(__file__).resolve().parent / "fixture" /
                     "disk").resolve()


def build_l1_workspace(
    disk_root: str | Path | None = None,
    *,
    agent_id: str = "mirage-eval",
    session_id: str = "default",
) -> Workspace:
    """Construct an L1 (synthetic, offline) workspace for ACME Corp.

    Args:
        disk_root (str | Path | None): Filesystem root containing the
            seeded subtrees.
        agent_id (str): Agent identifier for session isolation.
        session_id (str): Session identifier.
    """
    root = Path(disk_root or DEFAULT_DISK_ROOT).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(
            f"disk root {root} not found - run `uv run mirage-eval seed "
            f"--scenario acme_corp` first")
    return Workspace(
        {
            "/": (RAMResource(), MountMode.WRITE),
            "/slack": (FakeSlackResource(str(root / "slack")), MountMode.READ),
            "/sheets":
            (FakeGSheetsResource(str(root / "sheets")), MountMode.READ),
            "/gdocs": (FakeGDocsResource(str(root / "gdocs")), MountMode.READ),
            "/tickets":
            (FakeTicketingResource(str(root / "tickets")), MountMode.WRITE),
            "/github":
            (FakeGitHubResource(str(root / "github")), MountMode.READ),
            "/pagerduty":
            (FakePagerDutyResource(str(root / "pagerduty")), MountMode.READ),
            "/datadog":
            (FakeDatadogResource(str(root / "datadog")), MountMode.READ),
            "/finance":
            (DiskResource(root=str(root / "finance")), MountMode.READ),
            "/customers":
            (DiskResource(root=str(root / "customers")), MountMode.READ),
            "/compliance":
            (DiskResource(root=str(root / "compliance")), MountMode.READ),
        },
        mode=MountMode.WRITE,
        agent_id=agent_id,
        session_id=session_id,
    )
