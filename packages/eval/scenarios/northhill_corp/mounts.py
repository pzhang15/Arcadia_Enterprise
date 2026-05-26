from pathlib import Path

from mirage import MountMode, RAMResource, Workspace
# yapf: disable
from mirage_eval.fixtures import (FakeComplianceResource,
                                  FakeCustomersResource, FakeDatadogResource,
                                  FakeFinanceResource, FakeGDocsResource,
                                  FakeGitHubResource, FakeGSheetsResource,
                                  FakePagerDutyResource, FakePostgresResource,
                                  FakeS3Resource, FakeSlackResource,
                                  FakeTicketingResource)

# yapf: enable

DEFAULT_DISK_ROOT = (Path(__file__).resolve().parent / "fixture" /
                     "disk").resolve()


def build_l1_workspace(
    disk_root: str | Path | None = None,
    *,
    agent_id: str = "mirage-eval",
    session_id: str = "default",
) -> Workspace:
    """Construct an L1 (synthetic, offline) workspace for NorthHill Corp.

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
            f"--scenario northhill_corp` first")
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
            (FakeFinanceResource(str(root / "finance")), MountMode.READ),
            "/customers":
            (FakeCustomersResource(str(root / "customers")), MountMode.READ),
            "/compliance":
            (FakeComplianceResource(str(root / "compliance")), MountMode.READ),
            "/database":
            (FakePostgresResource(str(root / "database")), MountMode.READ),
            "/s3": (FakeS3Resource(str(root / "s3")), MountMode.READ),
        },
        mode=MountMode.WRITE,
        agent_id=agent_id,
        session_id=session_id,
    )
