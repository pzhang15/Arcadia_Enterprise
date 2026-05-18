import os

import mirage.core.github._client as github_client
import mirage.core.slack._client as slack_client
from mirage import MountMode, RAMResource, Workspace
from mirage.resource.github.github import GitHubResource
from mirage.resource.slack.config import SlackConfig
from mirage.resource.slack.slack import SlackResource

from mirage_eval.fixtures import (FakeDatadogResource, FakePagerDutyResource,
                                  FakeTicketingResource)
from scenarios.meridian_labs.mounts import DEFAULT_DISK_ROOT

MOCK_URL = os.environ.get("MOCK_SERVICES_URL", "http://localhost:3000")


def _patch_base_urls() -> None:
    """Redirect Mirage's hardcoded API base URLs to the mock server."""
    slack_client.SLACK_API = f"{MOCK_URL}/slack/api"
    github_client.API_BASE = f"{MOCK_URL}/github"


def build_docker_workspace(
    *,
    agent_id: str = "mirage-eval",
    session_id: str = "default",
    disk_root=None,
) -> Workspace:
    """Workspace with real Slack + GitHub resources pointed at mock servers.

    PagerDuty, Datadog, and Ticketing stay disk-backed (FakeXxxResource)
    because the core library has no native resource for them. The mock
    HTTP server still runs for direct API testing of those services.

    Args:
        agent_id (str): Agent identifier.
        session_id (str): Session identifier.
        disk_root: Override for the seed data root (used by tests).
    """
    _patch_base_urls()
    root = disk_root or DEFAULT_DISK_ROOT
    slack = SlackResource(config=SlackConfig(token="mock-token"))
    github = GitHubResource(config={"token": "mock-token"})
    return Workspace(
        {
            "/": (RAMResource(), MountMode.WRITE),
            "/slack": (slack, MountMode.READ),
            "/tickets": (FakeTicketingResource(str(root / "tickets")),
                         MountMode.WRITE),
            "/github": (github, MountMode.READ),
            "/pagerduty": (FakePagerDutyResource(str(root / "pagerduty")),
                           MountMode.READ),
            "/datadog": (FakeDatadogResource(str(root / "datadog")),
                         MountMode.READ),
        },
        mode=MountMode.WRITE,
        agent_id=agent_id,
        session_id=session_id,
    )
