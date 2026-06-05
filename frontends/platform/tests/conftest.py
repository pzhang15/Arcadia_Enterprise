import os
import sys
import tempfile
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_PLATFORM_DIR = Path(__file__).resolve().parent.parent
if str(_PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(_PLATFORM_DIR))

_TEST_DB = Path(tempfile.gettempdir()) / f"arcadia_test_{uuid.uuid4().hex}.db"
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_TEST_DB}")
os.environ.setdefault("STORE_FLUSH_INTERVAL", "0.1")

import server  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(server.app) as test_client:
        yield test_client


@pytest.fixture
def make_ws(client):
    created: list[str] = []

    def _make(
        mounts: list[dict] | None = None,
        standup: bool = False,
        name: str = "itest",
        template_id: str = "custom",
    ) -> str:
        if mounts is None:
            mounts = [
                {"path": "/pagerduty", "mode": "ro"},
                {"path": "/scratch", "mode": "rw"},
            ]
        res = client.post(
            "/api/console/workspaces",
            json={"name": name, "template_id": template_id, "mounts": mounts},
        )
        assert res.status_code == 200, res.text
        ws_id = res.json()["id"]
        created.append(ws_id)
        if standup:
            standup_res = client.post(
                f"/api/console/workspaces/{ws_id}/standup")
            assert standup_res.status_code == 200, standup_res.text
        return ws_id

    yield _make

    for ws_id in created:
        client.delete(f"/api/console/workspaces/{ws_id}")
