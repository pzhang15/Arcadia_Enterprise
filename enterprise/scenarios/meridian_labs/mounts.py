from pathlib import Path

from mirage import MountMode, RAMResource, Workspace

from mirage_eval.fixtures import (FakeDatadogResource, FakeGitHubResource,
                                  FakePagerDutyResource, FakeSlackResource,
                                  FakeTicketingResource)

DEFAULT_DISK_ROOT = (Path(__file__).resolve().parent / "fixture"
                     / "disk").resolve()


def build_l1_workspace(
    disk_root: str | Path | None = None,
    *,
    agent_id: str = "mirage-eval",
    session_id: str = "default",
) -> Workspace:
    """Construct an L1 (synthetic, offline) workspace for Meridian Labs.

    Args:
        disk_root (str | Path | None): Filesystem root containing the
            seeded slack/tickets/github/pagerduty/datadog subtrees.
        agent_id (str): Agent identifier for session isolation.
        session_id (str): Session identifier.
    """
    root = Path(disk_root or DEFAULT_DISK_ROOT).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(
            f"disk root {root} not found - run `uv run mirage-eval seed "
            f"--scenario meridian_labs` first")
    return Workspace(
        {
            "/": (RAMResource(), MountMode.WRITE),
            "/slack": (FakeSlackResource(str(root / "slack")),
                       MountMode.READ),
            "/tickets": (FakeTicketingResource(str(root / "tickets")),
                         MountMode.WRITE),
            "/github": (FakeGitHubResource(str(root / "github")),
                        MountMode.READ),
            "/pagerduty": (FakePagerDutyResource(str(root / "pagerduty")),
                           MountMode.READ),
            "/datadog": (FakeDatadogResource(str(root / "datadog")),
                         MountMode.READ),
        },
        mode=MountMode.WRITE,
        agent_id=agent_id,
        session_id=session_id,
    )
